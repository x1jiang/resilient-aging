"""
Resilient Ager identification and classification.

This module implements the core algorithm for identifying resilient agers -
individuals who remain disease-free beyond population-expected age thresholds.

The algorithm:
1. Calculates cumulative disease incidence by age
2. Determines population thresholds (median and 75th percentile onset ages)
3. Identifies individuals disease-free beyond the 75th percentile threshold
4. Classifies them as resilient agers
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from .prevalence import (
    calculate_age_at_diagnosis,
    calculate_cumulative_incidence,
    get_percentile_onset_age,
)
from .concept_sets import ConceptSet, DISEASE_CONCEPTS


@dataclass
class PopulationThresholds:
    """
    Population-level disease onset thresholds.
    
    Attributes:
        disease_key: Key identifying the disease
        median_onset_age: Age by which 50% of affected individuals are diagnosed
        percentile_75_onset_age: Age by which 75% are diagnosed (resilience threshold)
        percentile_90_onset_age: Age by which 90% are diagnosed
        n_total: Total population size
        n_affected: Number with the condition
        prevalence: Overall disease prevalence
    """
    disease_key: str
    median_onset_age: Optional[float]
    percentile_75_onset_age: Optional[float]
    percentile_90_onset_age: Optional[float]
    n_total: int
    n_affected: int
    prevalence: float


@dataclass
class ResilientAgerResult:
    """
    Result of resilient ager classification for an individual.
    
    Attributes:
        person_id: OMOP person identifier
        current_age: Current age in years
        has_condition: Whether the person has the condition
        age_at_diagnosis: Age at first diagnosis (if applicable)
        is_resilient: Whether classified as resilient ager
        resilience_score: Degree of resilience (years beyond threshold)
        classification: Text classification (resilient_ager, typical, affected)
    """
    person_id: int
    current_age: float
    has_condition: bool
    age_at_diagnosis: Optional[float]
    is_resilient: bool
    resilience_score: float
    classification: str


def get_population_thresholds(
    session: Session,
    disease_key: str,
    concept_set: Optional[ConceptSet] = None
) -> PopulationThresholds:
    """
    Calculate population-level disease onset thresholds.
    
    These thresholds define the ages by which certain percentiles of the
    affected population have been diagnosed, used as benchmarks for
    identifying resilient agers.
    
    Args:
        session: SQLAlchemy session
        disease_key: Key from DISEASE_CONCEPTS dictionary
        concept_set: Optional custom concept set (uses DISEASE_CONCEPTS if None)
        
    Returns:
        PopulationThresholds with calculated values
    """
    if concept_set is None:
        concept_set = DISEASE_CONCEPTS.get(disease_key)
        if concept_set is None:
            raise ValueError(f"Unknown disease key: {disease_key}")
    
    concept_ids = concept_set.concept_ids
    
    # Get diagnosis ages for all persons
    df = calculate_age_at_diagnosis(session, concept_ids)
    
    n_total = len(df)
    n_affected = df['has_condition'].sum()
    prevalence = n_affected / n_total if n_total > 0 else 0
    
    # Calculate percentile ages among those affected
    median_age = get_percentile_onset_age(df, 50.0)
    p75_age = get_percentile_onset_age(df, 75.0)
    p90_age = get_percentile_onset_age(df, 90.0)
    
    return PopulationThresholds(
        disease_key=disease_key,
        median_onset_age=median_age,
        percentile_75_onset_age=p75_age,
        percentile_90_onset_age=p90_age,
        n_total=n_total,
        n_affected=n_affected,
        prevalence=prevalence,
    )


def classify_individual(
    person_id: int,
    current_age: float,
    has_condition: bool,
    age_at_diagnosis: Optional[float],
    threshold_age: float,
    min_age_for_resilience: float = 60.0
) -> ResilientAgerResult:
    """
    Classify a single individual as resilient ager or not.
    
    Args:
        person_id: OMOP person ID
        current_age: Current age in years
        has_condition: Whether person has the condition
        age_at_diagnosis: Age at diagnosis if applicable
        threshold_age: 75th percentile threshold age
        min_age_for_resilience: Minimum age to be considered for resilience
        
    Returns:
        ResilientAgerResult with classification
    """
    # Persons with the condition cannot be resilient for that condition
    if has_condition:
        resilience_score = 0.0
        if age_at_diagnosis and age_at_diagnosis > threshold_age:
            # Late-onset - somewhat resilient
            classification = "late_onset"
            resilience_score = age_at_diagnosis - threshold_age
        else:
            classification = "affected"
        
        return ResilientAgerResult(
            person_id=person_id,
            current_age=current_age,
            has_condition=True,
            age_at_diagnosis=age_at_diagnosis,
            is_resilient=False,
            resilience_score=resilience_score,
            classification=classification,
        )
    
    # Disease-free individuals
    if current_age >= threshold_age and current_age >= min_age_for_resilience:
        # Resilient ager: disease-free beyond 75th percentile threshold
        is_resilient = True
        resilience_score = current_age - threshold_age
        classification = "resilient_ager"
    elif current_age >= min_age_for_resilience:
        # Older but hasn't reached threshold yet
        is_resilient = False
        resilience_score = 0.0
        classification = "disease_free_not_threshold"
    else:
        # Too young to classify
        is_resilient = False
        resilience_score = 0.0
        classification = "too_young"
    
    return ResilientAgerResult(
        person_id=person_id,
        current_age=current_age,
        has_condition=False,
        age_at_diagnosis=None,
        is_resilient=is_resilient,
        resilience_score=resilience_score,
        classification=classification,
    )


def classify_resilient_agers(
    session: Session,
    disease_key: str,
    concept_set: Optional[ConceptSet] = None,
    min_age: float = 60.0,
    percentile_threshold: float = 75.0
) -> pd.DataFrame:
    """
    Classify all individuals as resilient agers or not for a given disease.
    
    The algorithm:
    1. Calculate the age by which X% of affected individuals are diagnosed
    2. Identify disease-free individuals older than this threshold age
    3. Classify them as resilient agers
    
    Args:
        session: SQLAlchemy session
        disease_key: Key from DISEASE_CONCEPTS
        concept_set: Optional custom concept set
        min_age: Minimum age to consider for resilience classification
        percentile_threshold: Percentile threshold (default 75)
        
    Returns:
        DataFrame with person_id, classification, and resilience metrics
    """
    if concept_set is None:
        concept_set = DISEASE_CONCEPTS.get(disease_key)
        if concept_set is None:
            raise ValueError(f"Unknown disease key: {disease_key}")
    
    # Get population thresholds
    thresholds = get_population_thresholds(session, disease_key, concept_set)
    
    # Get threshold age based on specified percentile
    if percentile_threshold == 75.0:
        threshold_age = thresholds.percentile_75_onset_age
    elif percentile_threshold == 90.0:
        threshold_age = thresholds.percentile_90_onset_age
    else:
        # Calculate custom percentile
        df = calculate_age_at_diagnosis(session, concept_set.concept_ids)
        threshold_age = get_percentile_onset_age(df, percentile_threshold)
    
    if threshold_age is None:
        # No one with this condition - everyone is "resilient"
        threshold_age = 100.0
    
    # Get all individuals with their diagnosis status
    df = calculate_age_at_diagnosis(session, concept_set.concept_ids)
    
    # Classify each individual
    results = []
    for _, row in df.iterrows():
        result = classify_individual(
            person_id=row['person_id'],
            current_age=row['current_age'],
            has_condition=row['has_condition'],
            age_at_diagnosis=row['age_at_diagnosis'],
            threshold_age=threshold_age,
            min_age_for_resilience=min_age,
        )
        results.append({
            'person_id': result.person_id,
            'current_age': result.current_age,
            'has_condition': result.has_condition,
            'age_at_diagnosis': result.age_at_diagnosis,
            'is_resilient': result.is_resilient,
            'resilience_score': result.resilience_score,
            'classification': result.classification,
            'disease_key': disease_key,
            'threshold_age': threshold_age,
        })
    
    return pd.DataFrame(results)


def create_cohort(
    session: Session,
    disease_key: str,
    cohort_type: str = "resilient_ager",
    min_age: float = 60.0
) -> pd.DataFrame:
    """
    Create a cohort of resilient agers or comparison group.
    
    Args:
        session: SQLAlchemy session
        disease_key: Disease to analyze
        cohort_type: "resilient_ager", "affected", or "typical"
        min_age: Minimum age for cohort
        
    Returns:
        DataFrame with cohort members
    """
    df = classify_resilient_agers(session, disease_key, min_age=min_age)
    
    if cohort_type == "resilient_ager":
        cohort = df[df['is_resilient'] == True]
    elif cohort_type == "affected":
        cohort = df[df['has_condition'] == True]
    elif cohort_type == "typical":
        cohort = df[(df['is_resilient'] == False) & (df['has_condition'] == False)]
    else:
        raise ValueError(f"Unknown cohort type: {cohort_type}")
    
    return cohort


def compare_cohorts(
    session: Session,
    disease_key: str,
    min_age: float = 60.0
) -> dict:
    """
    Generate comparison statistics between resilient and typical agers.
    
    Args:
        session: SQLAlchemy session
        disease_key: Disease to analyze
        min_age: Minimum age for analysis
        
    Returns:
        Dictionary with comparison metrics
    """
    df = classify_resilient_agers(session, disease_key, min_age=min_age)
    
    # Filter to those meeting age threshold
    df_eligible = df[df['current_age'] >= min_age]
    
    total = len(df_eligible)
    resilient = df_eligible[df_eligible['is_resilient'] == True]
    affected = df_eligible[df_eligible['has_condition'] == True]
    typical = df_eligible[(df_eligible['is_resilient'] == False) & 
                          (df_eligible['has_condition'] == False)]
    
    return {
        'disease_key': disease_key,
        'min_age': min_age,
        'total_eligible': total,
        'n_resilient': len(resilient),
        'n_affected': len(affected),
        'n_typical': len(typical),
        'pct_resilient': len(resilient) / total * 100 if total > 0 else 0,
        'pct_affected': len(affected) / total * 100 if total > 0 else 0,
        'avg_age_resilient': resilient['current_age'].mean() if len(resilient) > 0 else None,
        'avg_age_affected': affected['current_age'].mean() if len(affected) > 0 else None,
        'avg_resilience_score': resilient['resilience_score'].mean() if len(resilient) > 0 else None,
        'threshold_age': df_eligible['threshold_age'].iloc[0] if len(df_eligible) > 0 else None,
    }


def run_multi_disease_analysis(
    session: Session,
    disease_keys: Optional[list[str]] = None,
    min_age: float = 60.0
) -> pd.DataFrame:
    """
    Run resilient ager analysis across multiple diseases.
    
    Args:
        session: SQLAlchemy session
        disease_keys: List of diseases to analyze (default: all)
        min_age: Minimum age for analysis
        
    Returns:
        DataFrame with results for each disease
    """
    if disease_keys is None:
        disease_keys = list(DISEASE_CONCEPTS.keys())
    
    results = []
    for disease_key in disease_keys:
        try:
            comparison = compare_cohorts(session, disease_key, min_age)
            thresholds = get_population_thresholds(session, disease_key)
            
            results.append({
                **comparison,
                'median_onset_age': thresholds.median_onset_age,
                'percentile_75_onset_age': thresholds.percentile_75_onset_age,
            })
        except Exception as e:
            # Skip diseases with issues
            print(f"Warning: Could not analyze {disease_key}: {e}")
            continue
    
    return pd.DataFrame(results)
