import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from db_models import Search, Route as RouteDB
from models import (
    SearchResultsResponse,
    RetrosynthesisTree,
    CatalogEntry as CatalogEntryModel,
)
from retrosynthesis_search import build_retrosynthesis_tree, RouteData

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search/{search_id}/results", response_model=SearchResultsResponse)
async def get_search_results(
    search_id: str,
    min_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    search = db.query(Search).filter(Search.id == search_id).first()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found"
        )

    query = db.query(RouteDB).filter(RouteDB.search_id == search_id)
    if min_score is not None:
        query = query.filter(RouteDB.score >= min_score)
    routes = query.order_by(desc(RouteDB.score)).all()

    retrosynthesis_trees = []
    for route in routes:
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
