"""Backend API service."""
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.config import settings
from backend.database import get_db, engine, Base
from backend.db_models import Search, Route as RouteDB, RouteMolecule, CatalogEntry as CatalogEntryDB, Reaction as ReactionDB
from backend.models import (
    SearchCreateRequest,
    SearchCreateResponse,
    SearchStatusResponse,
    SearchResultsResponse,
    SearchUpdate,
    UpdateResponse,
    HealthResponse,
    RetrosynthesisTree,
    Route as RouteModel,
    Molecule as MoleculeModel,
    CatalogEntry as CatalogEntryModel,
    Reaction as ReactionModel,
)
from backend.retrosynthesis_search import SearchStatus, build_retrosynthesis_tree, RouteData

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Retrosynthesis Backend API",
    description="Backend API for retrosynthesis search requests",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@app.post("/api/search", response_model=SearchCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_search(
    request: SearchCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new retrosynthesis search."""
    logger.info(f"Creating search for SMILES: {request.smiles}")

    # Create search record
    search = Search(
        smiles=request.smiles,
        status=SearchStatus.PENDING.value
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    # Trigger microservice asynchronously
    try:
        async with httpx.AsyncClient() as client:
            # Use callback host from settings
            callback_url = f"http://{settings.CALLBACK_HOST}:{settings.API_PORT}/api/search/{search.id}/update"
            microservice_request = {
                "smiles": request.smiles,
                "callback_url": callback_url
            }
            response = await client.post(
                f"{settings.MICROSERVICE_URL}/start_search",
                json=microservice_request,
                timeout=5.0
            )
            response.raise_for_status()
            logger.info(f"Microservice search initiated for search_id: {search.id}")
    except Exception as e:
        logger.error(f"Failed to initiate microservice search: {e}")
        search.status = SearchStatus.FAILED.value
        search.error_message = f"Failed to initiate search: {str(e)}"
        db.commit()

    return SearchCreateResponse(id=search.id)


@app.get("/api/search/{search_id}/status", response_model=SearchStatusResponse)
async def get_search_status(
    search_id: str,
    db: Session = Depends(get_db)
):
    """Get the status of a search."""
    search = db.query(Search).filter(Search.id == search_id).first()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found"
        )

    return SearchStatusResponse(
        id=search.id,
        smiles=search.smiles,
        status=SearchStatus(search.status),
        created_at=search.created_at.isoformat(),
        updated_at=search.updated_at.isoformat(),
        error_message=search.error_message
    )


@app.get("/api/search/{search_id}/results", response_model=SearchResultsResponse)
async def get_search_results(
    search_id: str,
    min_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get search results with optional filtering."""
    search = db.query(Search).filter(Search.id == search_id).first()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found"
        )

    # Query routes
    query = db.query(RouteDB).filter(RouteDB.search_id == search_id)
    if min_score is not None:
        query = query.filter(RouteDB.score >= min_score)
    routes = query.order_by(desc(RouteDB.score)).all()

    # Convert to response format
    retrosynthesis_trees = []
    for route in routes:
        # Build RouteData from database
        molecules_data = []
        for mol in route.molecules:
            catalog_entries_data = [
                CatalogEntryModel(
                    vendor_id=ce.vendor_id,
                    catalog_name=ce.catalog_name,
                    lead_time_weeks=ce.lead_time_weeks
                )
                for ce in mol.catalog_entries
            ]
            molecules_data.append({
                "smiles": mol.smiles,
                "catalog_entries": [ce.dict() for ce in catalog_entries_data]
            })

        reactions_data = []
        for reaction in route.reactions:
            import json
            sources = json.loads(reaction.sources) if isinstance(reaction.sources, str) else reaction.sources
            reactions_data.append({
                "name": reaction.name,
                "target": reaction.target,
                "sources": sources
            })

        route_data: RouteData = {
            "score": route.score,
            "molecules": molecules_data,
            "reactions": reactions_data
        }

        try:
            tree = build_retrosynthesis_tree(route_data)
            retrosynthesis_trees.append(RetrosynthesisTree(**tree))
        except Exception as e:
            logger.warning(f"Failed to build tree for route {route.id}: {e}")
            continue

    return SearchResultsResponse(
        search_id=search_id,
        total_routes=len(retrosynthesis_trees),
        routes=retrosynthesis_trees
    )


@app.post("/api/search/{search_id}/update", response_model=UpdateResponse)
async def update_search(
    search_id: str,
    update: SearchUpdate,
    db: Session = Depends(get_db)
):
    """Callback endpoint for microservice to post results."""
    logger.info(f"Received update for search {search_id}: {len(update.routes)} routes, complete={update.is_complete}")

    search = db.query(Search).filter(Search.id == search_id).first()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found"
        )

    try:
        # Store routes
        for route_model in update.routes:
            route_db = RouteDB(
                search_id=search_id,
                score=route_model.score
            )
            db.add(route_db)
            db.flush()

            # Store molecules
            for mol_model in route_model.molecules:
                route_mol = RouteMolecule(
                    route_id=route_db.id,
                    smiles=mol_model.smiles,
                    is_purchasable=bool(mol_model.catalog_entries)
                )
                db.add(route_mol)
                db.flush()

                # Store catalog entries
                for cat_entry in mol_model.catalog_entries:
                    catalog_entry = CatalogEntryDB(
                        molecule_id=route_mol.id,
                        vendor_id=cat_entry.vendor_id,
                        catalog_name=cat_entry.catalog_name,
                        lead_time_weeks=cat_entry.lead_time_weeks
                    )
                    db.add(catalog_entry)

            # Store reactions
            import json
            for reaction_model in route_model.reactions:
                reaction_db = ReactionDB(
                    route_id=route_db.id,
                    name=reaction_model.name,
                    target=reaction_model.target,
                    sources=json.dumps(reaction_model.sources)
                )
                db.add(reaction_db)

        # Update search status
        if update.error_message:
            search.status = SearchStatus.FAILED.value
            search.error_message = update.error_message
        elif update.is_complete:
            search.status = SearchStatus.COMPLETED.value
        else:
            search.status = SearchStatus.IN_PROGRESS.value

        db.commit()
        logger.info(f"Successfully updated search {search_id}")

        return UpdateResponse(status="ok")

    except Exception as e:
        logger.error(f"Error updating search {search_id}: {e}")
        db.rollback()
        search.status = SearchStatus.FAILED.value
        search.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update search: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
