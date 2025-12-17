"""
OMOP CDM Schema definitions using SQLAlchemy ORM.

This module defines the core OMOP Common Data Model tables needed for
the Resilient Aging algorithm:
- Person: Patient demographics and birth/death dates
- ConditionOccurrence: Diagnoses with dates
- ObservationPeriod: Valid observation windows
- Death: Mortality records (optional, death may be in Person table)
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, BigInteger, String, Date, DateTime, Float, ForeignKey,
    Index, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all OMOP CDM models."""
    pass


class Person(Base):
    """
    OMOP CDM Person table.
    
    Contains demographic information for each patient in the database.
    """
    __tablename__ = "person"
    
    person_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    gender_concept_id: Mapped[int] = mapped_column(Integer, nullable=False)
    year_of_birth: Mapped[int] = mapped_column(Integer, nullable=False)
    month_of_birth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    day_of_birth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    birth_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    death_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    race_concept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethnicity_concept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    provider_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    care_site_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    person_source_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gender_source_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    conditions: Mapped[list["ConditionOccurrence"]] = relationship(
        "ConditionOccurrence", back_populates="person"
    )
    observation_periods: Mapped[list["ObservationPeriod"]] = relationship(
        "ObservationPeriod", back_populates="person"
    )
    
    def get_birth_date(self) -> date:
        """Get birth date from available fields."""
        if self.birth_datetime:
            return self.birth_datetime.date()
        return date(
            self.year_of_birth,
            self.month_of_birth or 7,  # Default to July if unknown
            self.day_of_birth or 1     # Default to 1st if unknown
        )
    
    def get_age_at_date(self, reference_date: date) -> float:
        """Calculate age in years at a given date."""
        birth = self.get_birth_date()
        age_days = (reference_date - birth).days
        return age_days / 365.25
    
    def is_deceased(self) -> bool:
        """Check if person has a death date recorded."""
        return self.death_datetime is not None


class ConditionOccurrence(Base):
    """
    OMOP CDM Condition Occurrence table.
    
    Records patient diagnoses with start and end dates.
    """
    __tablename__ = "condition_occurrence"
    
    condition_occurrence_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.person_id"), nullable=False, index=True
    )
    condition_concept_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    condition_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    condition_start_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    condition_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    condition_end_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    condition_type_concept_id: Mapped[int] = mapped_column(Integer, nullable=False)
    condition_status_concept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stop_reason: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    provider_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    visit_occurrence_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    condition_source_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    condition_source_concept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    person: Mapped["Person"] = relationship("Person", back_populates="conditions")
    
    __table_args__ = (
        Index("idx_condition_person_concept", "person_id", "condition_concept_id"),
    )


class ObservationPeriod(Base):
    """
    OMOP CDM Observation Period table.
    
    Defines the span of time during which a person is expected to have
    clinical events recorded if they occur.
    """
    __tablename__ = "observation_period"
    
    observation_period_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.person_id"), nullable=False, index=True
    )
    observation_period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    observation_period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_type_concept_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Relationships
    person: Mapped["Person"] = relationship("Person", back_populates="observation_periods")


class Death(Base):
    """
    OMOP CDM Death table.
    
    Records mortality information. Note: Some OMOP implementations store
    death_datetime directly in the Person table instead.
    """
    __tablename__ = "death"
    
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.person_id"), primary_key=True
    )
    death_date: Mapped[date] = mapped_column(Date, nullable=False)
    death_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    death_type_concept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cause_concept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cause_source_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cause_source_concept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class ConceptAncestor(Base):
    """
    OMOP CDM Concept Ancestor table.
    
    Defines hierarchical relationships between concepts, enabling
    expansion of concept sets to include descendants.
    """
    __tablename__ = "concept_ancestor"
    
    ancestor_concept_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    descendant_concept_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    min_levels_of_separation: Mapped[int] = mapped_column(Integer, nullable=False)
    max_levels_of_separation: Mapped[int] = mapped_column(Integer, nullable=False)
    
    __table_args__ = (
        Index("idx_ancestor_desc", "ancestor_concept_id", "descendant_concept_id"),
    )


class Concept(Base):
    """
    OMOP CDM Concept table.
    
    Contains all standard concepts used in the OMOP vocabulary.
    """
    __tablename__ = "concept"
    
    concept_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain_id: Mapped[str] = mapped_column(String(20), nullable=False)
    vocabulary_id: Mapped[str] = mapped_column(String(20), nullable=False)
    concept_class_id: Mapped[str] = mapped_column(String(20), nullable=False)
    standard_concept: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    concept_code: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    invalid_reason: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
