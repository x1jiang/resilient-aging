"""
Resilient Aging - Identify resilient agers from OMOP CDM data

This package implements the Resilient Aging phenotype identification algorithm,
which classifies individuals who remain disease-free beyond population-expected
age thresholds as "resilient agers".
"""

__version__ = "0.1.0"

from .database import Database, create_engine_from_config
from .omop_schema import Person, ConditionOccurrence, ObservationPeriod, Death
from .concept_sets import ConceptSet, DISEASE_CONCEPTS
from .prevalence import (
    calculate_age_at_diagnosis,
    calculate_cumulative_incidence,
    calculate_disease_free_survival,
)
from .resilient_ager import (
    get_population_thresholds,
    classify_resilient_agers,
    create_cohort,
)

__all__ = [
    "Database",
    "create_engine_from_config",
    "Person",
    "ConditionOccurrence",
    "ObservationPeriod",
    "Death",
    "ConceptSet",
    "DISEASE_CONCEPTS",
    "calculate_age_at_diagnosis",
    "calculate_cumulative_incidence",
    "calculate_disease_free_survival",
    "get_population_thresholds",
    "classify_resilient_agers",
    "create_cohort",
]
