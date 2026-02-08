from pydantic import BaseModel

class SearchRequest(BaseModel):
    smiles: str
    callback_url: str

class CatalogEntry(BaseModel):
    vendor_id: str
    catalog_name: str
    lead_time_weeks: float

class Molecule(BaseModel):
    smiles: str
    catalog_entries: list[CatalogEntry]

class Reaction(BaseModel):
    name: str
    target: str
    sources: list[str]

class Route(BaseModel):
    score: float
    molecules: list[Molecule]
    reactions: list[Reaction]

class SearchUpdate(BaseModel):
    routes: list[Route]
    is_complete: bool = False
    error_message: str | None = None
