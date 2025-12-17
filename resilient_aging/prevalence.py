"""
Age-specific disease prevalence and cumulative incidence calculations.

This module implements the core epidemiological calculations for the
Resilient Aging algorithm:
- Age at first diagnosis
- Disease prevalence by age group
- Cumulative incidence curves
- Disease-free survival estimates
"""

from datetime import date
from typing import Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .omop_schema import Person, ConditionOccurrence, ObservationPeriod
from .concept_sets import ConceptSet


def calculate_age_at_diagnosis(
    session: Session,
    concept_ids: list[int],
    reference_date: Optional[date] = None
) -> pd.DataFrame:
    """
    Calculate age at first diagnosis for each person with the condition.
    
    Args:
        session: SQLAlchemy session
        concept_ids: List of OMOP concept IDs for the condition
        reference_date: Reference date for calculating current age (default: today)
        
    Returns:
        DataFrame with columns: person_id, age_at_diagnosis, diagnosis_date,
        is_deceased, current_age
    """
    if reference_date is None:
        reference_date = date.today()
    
    # Query first diagnosis date for each person
    subquery = (
        session.query(
            ConditionOccurrence.person_id,
            func.min(ConditionOccurrence.condition_start_date).label('first_diagnosis_date')
        )
        .filter(ConditionOccurrence.condition_concept_id.in_(concept_ids))
        .group_by(ConditionOccurrence.person_id)
        .subquery()
    )
    
    # Join with person table to get demographics
    results = (
        session.query(
            Person.person_id,
            Person.year_of_birth,
            Person.month_of_birth,
            Person.day_of_birth,
            Person.death_datetime,
            subquery.c.first_diagnosis_date
        )
        .outerjoin(subquery, Person.person_id == subquery.c.person_id)
        .all()
    )
    
    data = []
    for row in results:
        birth_date = date(
            row.year_of_birth,
            row.month_of_birth or 7,
            row.day_of_birth or 1
        )
        
        current_age = (reference_date - birth_date).days / 365.25
        is_deceased = row.death_datetime is not None
        
        if row.first_diagnosis_date:
            age_at_diagnosis = (row.first_diagnosis_date - birth_date).days / 365.25
        else:
            age_at_diagnosis = None
        
        data.append({
            'person_id': row.person_id,
            'birth_date': birth_date,
            'age_at_diagnosis': age_at_diagnosis,
            'diagnosis_date': row.first_diagnosis_date,
            'is_deceased': is_deceased,
            'current_age': current_age,
            'has_condition': age_at_diagnosis is not None,
        })
    
    return pd.DataFrame(data)


def calculate_age_bins(
    df: pd.DataFrame,
    age_column: str = 'current_age',
    bin_size: int = 5,
    max_age: int = 100
) -> pd.DataFrame:
    """
    Bin ages into groups for prevalence calculation.
    
    Args:
        df: DataFrame with age data
        age_column: Name of column containing ages
        bin_size: Width of each age bin in years
        max_age: Maximum age to include
        
    Returns:
        DataFrame with added 'age_bin' column
    """
    bins = list(range(0, max_age + bin_size, bin_size))
    labels = [f"{b}-{b+bin_size-1}" for b in bins[:-1]]
    
    df = df.copy()
    df['age_bin'] = pd.cut(df[age_column], bins=bins, labels=labels, right=False)
    return df


def calculate_prevalence_by_age(
    df: pd.DataFrame,
    age_column: str = 'current_age',
    condition_column: str = 'has_condition',
    bin_size: int = 5
) -> pd.DataFrame:
    """
    Calculate disease prevalence by age group.
    
    Args:
        df: DataFrame with patient data
        age_column: Column with ages
        condition_column: Boolean column indicating disease presence
        bin_size: Width of age bins
        
    Returns:
        DataFrame with prevalence by age bin
    """
    df = calculate_age_bins(df, age_column, bin_size)
    
    prevalence = df.groupby('age_bin').agg(
        n_total=('person_id', 'count'),
        n_with_condition=(condition_column, 'sum')
    ).reset_index()
    
    prevalence['prevalence'] = prevalence['n_with_condition'] / prevalence['n_total']
    prevalence['prevalence_pct'] = prevalence['prevalence'] * 100
    
    return prevalence


def calculate_cumulative_incidence(
    session: Session,
    concept_ids: list[int],
    max_age: int = 100,
    age_step: float = 1.0
) -> pd.DataFrame:
    """
    Calculate cumulative incidence of disease by age.
    
    Uses a simplified survival analysis approach where we calculate
    the proportion of people who have developed the disease by each age.
    
    Args:
        session: SQLAlchemy session
        concept_ids: List of condition concept IDs
        max_age: Maximum age to calculate
        age_step: Age increment for calculation
        
    Returns:
        DataFrame with columns: age, cumulative_incidence, n_at_risk, n_events
    """
    # Get all persons with their diagnosis ages
    df = calculate_age_at_diagnosis(session, concept_ids)
    
    ages = np.arange(0, max_age + age_step, age_step)
    results = []
    
    for age in ages:
        # Number at risk: persons who were alive and disease-free up to this age
        at_risk = df[
            (df['current_age'] >= age) |  # Still alive past this age
            ((df['age_at_diagnosis'].notna()) & (df['age_at_diagnosis'] >= age)) |  # Got disease after this age
            (df['is_deceased'] & (df['current_age'] >= age))  # Died after this age
        ]
        n_at_risk = len(at_risk)
        
        # Events: persons who developed disease by this age
        events = df[
            (df['age_at_diagnosis'].notna()) & 
            (df['age_at_diagnosis'] <= age)
        ]
        n_events = len(events)
        
        # Cumulative incidence
        cum_inc = n_events / len(df) if len(df) > 0 else 0
        
        results.append({
            'age': age,
            'n_at_risk': n_at_risk,
            'n_events': n_events,
            'n_total': len(df),
            'cumulative_incidence': cum_inc,
            'cumulative_incidence_pct': cum_inc * 100,
        })
    
    return pd.DataFrame(results)


def calculate_disease_free_survival(
    session: Session,
    concept_ids: list[int],
    max_age: int = 100
) -> pd.DataFrame:
    """
    Calculate disease-free survival probability by age.
    
    This is the complement of cumulative incidence - the probability
    of remaining disease-free at each age.
    
    Args:
        session: SQLAlchemy session
        concept_ids: List of condition concept IDs
        max_age: Maximum age to calculate
        
    Returns:
        DataFrame with age and disease-free survival probability
    """
    cum_inc = calculate_cumulative_incidence(session, concept_ids, max_age)
    cum_inc['disease_free_survival'] = 1 - cum_inc['cumulative_incidence']
    cum_inc['disease_free_pct'] = cum_inc['disease_free_survival'] * 100
    
    return cum_inc


def get_age_at_threshold(
    cum_inc_df: pd.DataFrame,
    threshold: float = 0.5
) -> Optional[float]:
    """
    Find the age at which cumulative incidence reaches a threshold.
    
    Args:
        cum_inc_df: DataFrame from calculate_cumulative_incidence
        threshold: Cumulative incidence threshold (0-1)
        
    Returns:
        Age at which threshold is reached, or None if never reached
    """
    above_threshold = cum_inc_df[cum_inc_df['cumulative_incidence'] >= threshold]
    
    if len(above_threshold) == 0:
        return None
    
    return above_threshold['age'].iloc[0]


def get_percentile_onset_age(
    df: pd.DataFrame,
    percentile: float = 50.0
) -> Optional[float]:
    """
    Get the age at which a given percentile of affected individuals were diagnosed.
    
    Args:
        df: DataFrame with age_at_diagnosis column
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Age at the specified percentile of diagnosis, or None if no diagnoses
    """
    diagnosed = df[df['age_at_diagnosis'].notna()]['age_at_diagnosis']
    
    if len(diagnosed) == 0:
        return None
    
    return np.percentile(diagnosed, percentile)


def calculate_incidence_rate(
    session: Session,
    concept_ids: list[int],
    age_min: int = 0,
    age_max: int = 100
) -> float:
    """
    Calculate crude incidence rate for a condition.
    
    Returns incidence rate per 1000 person-years.
    
    Args:
        session: SQLAlchemy session
        concept_ids: Condition concept IDs
        age_min: Minimum age to include
        age_max: Maximum age to include
        
    Returns:
        Incidence rate per 1000 person-years
    """
    df = calculate_age_at_diagnosis(session, concept_ids)
    
    # Filter by age
    df = df[(df['current_age'] >= age_min) & (df['current_age'] <= age_max)]
    
    # Count new cases
    n_cases = df['has_condition'].sum()
    
    # Calculate person-years (simplified: average follow-up time)
    # This is a rough approximation
    total_persons = len(df)
    avg_followup_years = 5.0  # Assume 5 years average follow-up
    
    person_years = total_persons * avg_followup_years
    
    if person_years == 0:
        return 0.0
    
    return (n_cases / person_years) * 1000
