import asyncio
import logging
import random

import httpx
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from models import SearchRequest, SearchUpdate, Route, Molecule, Reaction, CatalogEntry
from get_routes import get_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reatrosynthesis Microservice",
    description="Microservice for processing retrosynthesis searches",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def process_search_async(smiles: str, callback_url: str, batch_size: int = 1):
    logger.info(f"Starting search processing for SMILES: {smiles}, callback: {callback_url}")

    try:
        route_batches = list(get_routes(smiles, batch_size=batch_size))
        total_batches = len(route_batches)

        for batch_idx, (batch, is_last) in enumerate(route_batches, 1):
            logger.info(f"Processing batch {batch_idx}/{total_batches} ({len(batch)} routes)")

            routes = []
            for route_data in batch:
                molecules = [
                    Molecule(
                        smiles=mol["smiles"],
                        catalog_entries=[
                            CatalogEntry(**entry) for entry in mol.get("catalog_entries", [])
                        ]
                    )
                    for mol in route_data.get("molecules", [])
                ]

                reactions = [
                    Reaction(**rxn) for rxn in route_data.get("reactions", [])
                ]

                routes.append(Route(
                    score=route_data["score"],
                    molecules=molecules,
                    reactions=reactions
                ))

            update = SearchUpdate(
                routes=routes,
                is_complete=is_last
            )

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        callback_url,
                        json=update.dict(),
                        timeout=30.0
                    )
                    response.raise_for_status()
                    logger.info(f"Successfully posted batch {batch_idx}/{total_batches}")
                except Exception as e:
                    logger.error(f"Failed to post batch {batch_idx}: {e}")
                    error_update = SearchUpdate(
                        routes=[],
                        is_complete=True,
                        error_message=f"Failed to process batch {batch_idx}: {str(e)}"
                    )
                    try:
                        await client.post(callback_url, json=error_update.dict(), timeout=30.0)
                    except:
                        pass
                    raise

            if not is_last:
                delay = random.uniform(0.5, 2.0)
                await asyncio.sleep(delay)

        logger.info(f"Completed search processing for SMILES: {smiles}")

    except Exception as e:
        logger.error(f"Error processing search: {e}")
        error_update = SearchUpdate(
            routes=[],
            is_complete=True,
            error_message=str(e)
        )
        try:
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json=error_update.dict(), timeout=30.0)
        except:
            pass
        raise


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/start_search", status_code=status.HTTP_202_ACCEPTED)
async def start_search(request: SearchRequest):
    logger.info(f"Received search request for SMILES: {request.smiles}")

    asyncio.create_task(process_search_async(
        smiles=request.smiles,
        callback_url=request.callback_url,
        batch_size=1
    ))

    return {"status": "accepted", "message": "Search started"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
