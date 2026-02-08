"""SQLAlchemy database models."""
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from backend.database import Base
from backend.retrosynthesis_search import SearchStatus


class Search(Base):
    """Search request model."""
    __tablename__ = "searches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    smiles = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default=SearchStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    routes = relationship("Route", back_populates="search", cascade="all, delete-orphan")


class Route(Base):
    """Route model."""
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_id = Column(UUID(as_uuid=False), ForeignKey("searches.id"), nullable=False, index=True)
    score = Column(Float, nullable=False, index=True)

    search = relationship("Search", back_populates="routes")
    molecules = relationship("RouteMolecule", back_populates="route", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="route", cascade="all, delete-orphan")


class RouteMolecule(Base):
    """Molecule in a route."""
    __tablename__ = "route_molecules"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id = Column(UUID(as_uuid=False), ForeignKey("routes.id"), nullable=False, index=True)
    smiles = Column(String, nullable=False, index=True)
    is_purchasable = Column(Boolean, nullable=False, default=False)

    route = relationship("Route", back_populates="molecules")
    catalog_entries = relationship("CatalogEntry", back_populates="molecule", cascade="all, delete-orphan")


class CatalogEntry(Base):
    """Catalog entry for a molecule."""
    __tablename__ = "catalog_entries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(UUID(as_uuid=False), ForeignKey("route_molecules.id"), nullable=False, index=True)
    vendor_id = Column(String, nullable=False)
    catalog_name = Column(String, nullable=False)
    lead_time_weeks = Column(Float, nullable=False)

    molecule = relationship("RouteMolecule", back_populates="catalog_entries")


class Reaction(Base):
    """Reaction in a route."""
    __tablename__ = "reactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id = Column(UUID(as_uuid=False), ForeignKey("routes.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target = Column(String, nullable=False, index=True)
    sources = Column(Text, nullable=False)  # JSON array of SMILES strings

    route = relationship("Route", back_populates="reactions")
