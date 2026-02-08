import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import httpx
from config import settings
from database import get_db
from db_models import Search
from models import (
    SearchCreateRequest,
    SearchCreateResponse,
    SearchStatusResponse,
)
from retrosynthesis_search import SearchStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_search(
    request: SearchCreateRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"Creating search for SMILES: {request.smiles}")

    # Create search record
    search = Search(
        smiles=request.smiles,
        status=SearchStatus.PENDING.value
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    try:
        async with httpx.AsyncClient() as client:
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


@router.get("/search/{search_id}/status", response_model=SearchStatusResponse)
async def get_search_status(
    search_id: str,
    db: Session = Depends(get_db)
):
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
