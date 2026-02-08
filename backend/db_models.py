from datetime import datetime
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database import Base
from retrosynthesis_search import SearchStatus


class Search(Base):
    __tablename__ = "searches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    smiles = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default=SearchStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    routes = relationship("Route", back_populates="search", cascade="all, delete-orphan")


class Route(Base):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_id = Column(UUID(as_uuid=False), ForeignKey("searches.id"), nullable=False, index=True)
    score = Column(Float, nullable=False, index=True)

    search = relationship("Search", back_populates="routes")
    molecules = relationship("RouteMolecule", back_populates="route", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="route", cascade="all, delete-orphan")


class RouteMolecule(Base):
    __tablename__ = "route_molecules"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id = Column(UUID(as_uuid=False), ForeignKey("routes.id"), nullable=False, index=True)
    smiles = Column(String, nullable=False, index=True)
    is_purchasable = Column(Boolean, nullable=False, default=False)

    route = relationship("Route", back_populates="molecules")
    catalog_entries = relationship("CatalogEntry", back_populates="molecule", cascade="all, delete-orphan")


class CatalogEntry(Base):
    __tablename__ = "catalog_entries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(UUID(as_uuid=False), ForeignKey("route_molecules.id"), nullable=False, index=True)
    vendor_id = Column(String, nullable=False)
    catalog_name = Column(String, nullable=False)
    lead_time_weeks = Column(Float, nullable=False)

    molecule = relationship("RouteMolecule", back_populates="catalog_entries")


class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id = Column(UUID(as_uuid=False), ForeignKey("routes.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target = Column(String, nullable=False, index=True)
    sources = Column(Text, nullable=False)

    route = relationship("Route", back_populates="reactions")
