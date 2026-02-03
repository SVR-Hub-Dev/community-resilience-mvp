"""SQLAlchemy ORM models for the Knowledge Graph."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from models.models import Base, EMBEDDING_DIM


# ── Supported entity types (MVP subset of full ontology) ──────────────────────

ENTITY_TYPES = [
    "HazardType",
    "Community",
    "Agency",
    "Location",
    "Resource",
    "Action",
]

# ── Common relationship types ─────────────────────────────────────────────────

RELATIONSHIP_TYPES = [
    "occursIn",
    "hasHazardType",
    "serves",
    "responsibleFor",
    "locatedIn",
    "targets",
    "owns",
    "implementedBy",
    "dependsOn",
    "partOf",
]


# ── Models ────────────────────────────────────────────────────────────────────


class KGEntity(Base):
    """
    Knowledge graph entity (node).

    Represents a real-world concept extracted from documents:
    hazards, communities, agencies, locations, resources, or actions.
    """

    __tablename__ = "kg_entities"
    __table_args__ = (
        UniqueConstraint(
            "canonical_name", "entity_type", name="uq_kg_entity_canonical_type"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False)  # One of ENTITY_TYPES
    entity_subtype = Column(String(50))  # e.g. "bushfire", "urban"
    name = Column(Text, nullable=False)
    canonical_name = Column(Text)  # Normalized for dedup
    attributes = Column(JSON, server_default="{}")  # Type-specific key-value
    location_text = Column(Text)  # Human-readable location
    confidence_score = Column(Float, server_default="0.5")  # 0.0 - 1.0
    extraction_method = Column(String(50))  # "llm_extracted" or "manual"
    embedding = Column(Vector(EMBEDDING_DIM))  # For similarity search
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, server_default="false")

    # Relationships
    outgoing_relationships = relationship(
        "KGRelationship",
        foreign_keys="KGRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "KGRelationship",
        foreign_keys="KGRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )
    evidence = relationship(
        "KGEvidence",
        back_populates="entity",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<KGEntity(id={self.id}, type='{self.entity_type}', name='{self.name[:40]}')>"


class KGRelationship(Base):
    """
    Knowledge graph relationship (edge).

    Connects two entities with a typed, directed relationship.
    """

    __tablename__ = "kg_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_kg_relationship",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_entity_id = Column(
        Integer, ForeignKey("kg_entities.id", ondelete="CASCADE"), nullable=False
    )
    target_entity_id = Column(
        Integer, ForeignKey("kg_entities.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type = Column(String(100), nullable=False)
    attributes = Column(JSON, server_default="{}")
    confidence_score = Column(Float, server_default="0.5")
    extraction_method = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, server_default="false")

    # Relationships
    source_entity = relationship(
        "KGEntity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships",
    )
    target_entity = relationship(
        "KGEntity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships",
    )
    evidence = relationship(
        "KGEvidence",
        back_populates="kg_relationship",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<KGRelationship(id={self.id}, "
            f"src={self.source_entity_id} -{self.relationship_type}-> "
            f"tgt={self.target_entity_id})>"
        )


class KGEvidence(Base):
    """
    Provenance record linking a KG entity or relationship to its source document.

    Every extraction from a document produces evidence records so we can trace
    where each fact came from and how confident the extraction was.
    """

    __tablename__ = "kg_evidence"
    __table_args__ = (
        CheckConstraint(
            "(entity_id IS NOT NULL AND relationship_id IS NULL) OR "
            "(entity_id IS NULL AND relationship_id IS NOT NULL)",
            name="ck_kg_evidence_target",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("kg_entities.id", ondelete="CASCADE"))
    relationship_id = Column(
        Integer, ForeignKey("kg_relationships.id", ondelete="CASCADE")
    )
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    evidence_text = Column(Text)
    extraction_confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    entity = relationship("KGEntity", back_populates="evidence")
    kg_relationship = relationship("KGRelationship", back_populates="evidence")
    document = relationship("Document")

    def __repr__(self):
        target = (
            f"entity={self.entity_id}"
            if self.entity_id is not None
            else f"rel={self.relationship_id}"
        )
        return f"<KGEvidence(id={self.id}, {target}, doc={self.document_id})>"
