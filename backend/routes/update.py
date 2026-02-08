import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from db_models import (
    Search,
    Route as RouteDB,
    RouteMolecule,
    CatalogEntry as CatalogEntryDB,
    Reaction as ReactionDB,
)
from models import SearchUpdate, UpdateResponse
from retrosynthesis_search import SearchStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search/{search_id}/update", response_model=UpdateResponse)
async def update_search(
    search_id: str,
    update: SearchUpdate,
    db: Session = Depends(get_db)
):
    logger.info(f"Received update for search {search_id}: {len(update.routes)} routes, complete={update.is_complete}")

    search = db.query(Search).filter(Search.id == search_id).first()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found"
        )

    try:
        for route_model in update.routes:
            route_db = RouteDB(
                search_id=search_id,
                score=route_model.score
            )
            db.add(route_db)
            db.flush()

            for mol_model in route_model.molecules:
                route_mol = RouteMolecule(
                    route_id=route_db.id,
                    smiles=mol_model.smiles,
                    is_purchasable=bool(mol_model.catalog_entries)
                )
                db.add(route_mol)
                db.flush()

                for cat_entry in mol_model.catalog_entries:
                    catalog_entry = CatalogEntryDB(
                        molecule_id=route_mol.id,
                        vendor_id=cat_entry.vendor_id,
                        catalog_name=cat_entry.catalog_name,
                        lead_time_weeks=cat_entry.lead_time_weeks
                    )
                    db.add(catalog_entry)

            for reaction_model in route_model.reactions:
                reaction_db = ReactionDB(
                    route_id=route_db.id,
                    name=reaction_model.name,
                    target=reaction_model.target,
                    sources=json.dumps(reaction_model.sources)
                )
                db.add(reaction_db)

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
