"""Initialize database tables."""
from backend.database import engine, Base
from backend.db_models import Search, Route, RouteMolecule, CatalogEntry, Reaction

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
