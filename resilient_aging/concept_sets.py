"""
Disease concept sets for the Resilient Aging algorithm.

This module defines OMOP concept IDs for target diseases used in the
resilient aging classification. Concepts are based on SNOMED-CT codes
mapped to OMOP standard concept IDs.

Note: Actual concept IDs may vary depending on your OMOP vocabulary version.
These are representative examples that should be validated against your
specific OMOP instance.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConceptSet:
    """
    A set of OMOP concept IDs representing a disease or condition.
    
    Attributes:
        name: Human-readable name of the concept set
        concept_ids: Primary concept IDs for the condition
        description: Detailed description
        snomed_codes: Original SNOMED-CT codes (for reference)
        include_descendants: Whether to include descendant concepts
    """
    name: str
    concept_ids: list[int]
    description: str = ""
    snomed_codes: list[str] = field(default_factory=list)
    include_descendants: bool = True
    
    def get_all_concepts(self, session=None) -> list[int]:
        """
        Get all concept IDs including descendants if configured.
        
        Args:
            session: SQLAlchemy session for querying concept_ancestor table
            
        Returns:
            List of all applicable concept IDs
        """
        if not self.include_descendants or session is None:
            return self.concept_ids
        
        from .omop_schema import ConceptAncestor
        
        all_concepts = set(self.concept_ids)
        for concept_id in self.concept_ids:
            descendants = session.query(ConceptAncestor.descendant_concept_id).filter(
                ConceptAncestor.ancestor_concept_id == concept_id
            ).all()
            all_concepts.update(d[0] for d in descendants)
        
        return list(all_concepts)


# Standard OMOP concept IDs for key diseases
# These are representative IDs - verify against your OMOP vocabulary

DISEASE_CONCEPTS = {
    "type2_diabetes": ConceptSet(
        name="Type 2 Diabetes Mellitus",
        concept_ids=[201826, 443238, 4193704],  # OMOP standard concepts
        snomed_codes=["44054006"],
        description="Type 2 diabetes mellitus and related conditions"
    ),
    
    "alzheimer": ConceptSet(
        name="Alzheimer's Disease",
        concept_ids=[378419, 4182210],
        snomed_codes=["26929004"],
        description="Alzheimer's disease and dementia of Alzheimer type"
    ),
    
    "coronary_artery_disease": ConceptSet(
        name="Coronary Artery Disease",
        concept_ids=[316139, 4185932, 321318],
        snomed_codes=["53741008", "414545008"],
        description="Coronary artery disease, ischemic heart disease"
    ),
    
    "atrial_fibrillation": ConceptSet(
        name="Atrial Fibrillation",
        concept_ids=[313217, 4141360],
        snomed_codes=["49436004"],
        description="Atrial fibrillation and atrial flutter"
    ),
    
    "heart_failure": ConceptSet(
        name="Heart Failure",
        concept_ids=[316139, 319835],
        snomed_codes=["84114007"],
        description="Congestive heart failure and related conditions"
    ),
    
    "copd": ConceptSet(
        name="Chronic Obstructive Pulmonary Disease",
        concept_ids=[255573, 4063381],
        snomed_codes=["13645005"],
        description="COPD, chronic bronchitis, emphysema"
    ),
    
    "hypertension": ConceptSet(
        name="Essential Hypertension",
        concept_ids=[316866, 4028741],
        snomed_codes=["59621000"],
        description="Essential hypertension"
    ),
    
    "stroke": ConceptSet(
        name="Stroke",
        concept_ids=[443454, 4110189, 372924],
        snomed_codes=["230690007"],
        description="Cerebrovascular accident, ischemic and hemorrhagic stroke"
    ),
    
    "cancer_breast": ConceptSet(
        name="Breast Cancer",
        concept_ids=[4112853, 4180791],
        snomed_codes=["254837009"],
        description="Malignant neoplasm of breast"
    ),
    
    "cancer_prostate": ConceptSet(
        name="Prostate Cancer",
        concept_ids=[4163261, 4180792],
        snomed_codes=["399068003"],
        description="Malignant neoplasm of prostate"
    ),
    
    "cancer_colorectal": ConceptSet(
        name="Colorectal Cancer",
        concept_ids=[4180793, 4181483],
        snomed_codes=["363406005", "363414004"],
        description="Malignant neoplasm of colon and rectum"
    ),
    
    "osteoporosis": ConceptSet(
        name="Osteoporosis",
        concept_ids=[80180, 4097107],
        snomed_codes=["64859006"],
        description="Osteoporosis and related bone density disorders"
    ),
    
    "chronic_kidney_disease": ConceptSet(
        name="Chronic Kidney Disease",
        concept_ids=[46271022, 193782],
        snomed_codes=["709044004"],
        description="Chronic kidney disease stages 3-5"
    ),
    
    "parkinson": ConceptSet(
        name="Parkinson's Disease",
        concept_ids=[381270],
        snomed_codes=["49049000"],
        description="Parkinson's disease and parkinsonism"
    ),
}

# Gender concept IDs
GENDER_CONCEPTS = {
    "male": 8507,
    "female": 8532,
    "unknown": 0
}

# Ethnicity concept IDs
ETHNICITY_CONCEPTS = {
    "hispanic": 38003563,
    "not_hispanic": 38003564,
    "unknown": 0
}

# Race concept IDs
RACE_CONCEPTS = {
    "white": 8527,
    "black": 8516,
    "asian": 8515,
    "other": 8522,
    "unknown": 0
}


def get_concept_set(disease_key: str) -> Optional[ConceptSet]:
    """
    Get a concept set by its key name.
    
    Args:
        disease_key: Key from DISEASE_CONCEPTS dictionary
        
    Returns:
        ConceptSet if found, None otherwise
    """
    return DISEASE_CONCEPTS.get(disease_key)


def list_available_diseases() -> list[str]:
    """List all available disease keys."""
    return list(DISEASE_CONCEPTS.keys())


def get_all_disease_concepts() -> dict[str, list[int]]:
    """Get a mapping of disease keys to their concept IDs."""
    return {key: cs.concept_ids for key, cs in DISEASE_CONCEPTS.items()}
