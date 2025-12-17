"""
Synthetic OMOP data generator for testing the Resilient Aging algorithm.

Generates realistic patient populations with:
- Demographics following age/gender distributions
- Disease incidence patterns based on epidemiological data
- Mortality rates appropriate for age groups
"""

import random
from datetime import date, datetime, timedelta
from typing import Optional
import numpy as np

from .omop_schema import Base, Person, ConditionOccurrence, ObservationPeriod, Death
from .concept_sets import DISEASE_CONCEPTS, GENDER_CONCEPTS
from .database import Database


# Age-specific disease incidence rates (per 1000 person-years)
# Based on epidemiological literature - simplified for synthetic data
DISEASE_INCIDENCE_RATES = {
    "type2_diabetes": {
        (0, 30): 0.5,
        (30, 40): 2.0,
        (40, 50): 5.0,
        (50, 60): 10.0,
        (60, 70): 15.0,
        (70, 80): 18.0,
        (80, 100): 12.0,
    },
    "alzheimer": {
        (0, 60): 0.1,
        (60, 65): 1.0,
        (65, 70): 3.0,
        (70, 75): 8.0,
        (75, 80): 15.0,
        (80, 85): 30.0,
        (85, 100): 50.0,
    },
    "coronary_artery_disease": {
        (0, 40): 0.5,
        (40, 50): 3.0,
        (50, 60): 8.0,
        (60, 70): 15.0,
        (70, 80): 25.0,
        (80, 100): 30.0,
    },
    "atrial_fibrillation": {
        (0, 50): 0.2,
        (50, 60): 2.0,
        (60, 70): 5.0,
        (70, 80): 10.0,
        (80, 100): 20.0,
    },
    "heart_failure": {
        (0, 50): 0.5,
        (50, 60): 2.0,
        (60, 70): 5.0,
        (70, 80): 12.0,
        (80, 100): 25.0,
    },
    "copd": {
        (0, 40): 0.1,
        (40, 50): 2.0,
        (50, 60): 5.0,
        (60, 70): 10.0,
        (70, 80): 15.0,
        (80, 100): 18.0,
    },
    "hypertension": {
        (0, 30): 2.0,
        (30, 40): 8.0,
        (40, 50): 15.0,
        (50, 60): 25.0,
        (60, 70): 35.0,
        (70, 80): 45.0,
        (80, 100): 50.0,
    },
    "stroke": {
        (0, 50): 0.3,
        (50, 60): 2.0,
        (60, 70): 5.0,
        (70, 80): 12.0,
        (80, 100): 25.0,
    },
}

# Age-specific mortality rates (per 1000 person-years)
MORTALITY_RATES = {
    (0, 1): 6.0,
    (1, 5): 0.3,
    (5, 15): 0.15,
    (15, 25): 0.8,
    (25, 35): 1.0,
    (35, 45): 2.0,
    (45, 55): 4.0,
    (55, 65): 10.0,
    (65, 75): 25.0,
    (75, 85): 60.0,
    (85, 100): 150.0,
}


def get_rate_for_age(rates: dict, age: float) -> float:
    """Get the rate for a given age from age-banded rate dictionary."""
    for (min_age, max_age), rate in rates.items():
        if min_age <= age < max_age:
            return rate
    return 0.0


class SyntheticDataGenerator:
    """
    Generate synthetic OMOP-formatted data for testing.
    
    Creates a realistic patient population with:
    - Age distributions matching typical healthcare cohorts
    - Disease occurrence based on age-specific incidence
    - Mortality patterns matching population statistics
    """
    
    def __init__(
        self,
        n_patients: int = 10000,
        start_year: int = 2010,
        end_year: int = 2023,
        seed: Optional[int] = 42
    ):
        """
        Initialize the generator.
        
        Args:
            n_patients: Number of patients to generate
            start_year: Start of observation period
            end_year: End of observation period
            seed: Random seed for reproducibility
        """
        self.n_patients = n_patients
        self.start_year = start_year
        self.end_year = end_year
        self.reference_date = date(end_year, 12, 31)
        
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        self.persons: list[Person] = []
        self.conditions: list[ConditionOccurrence] = []
        self.observation_periods: list[ObservationPeriod] = []
        self.deaths: list[Death] = []
        
        self._condition_id = 1
        self._obs_period_id = 1
    
    def generate(self) -> None:
        """Generate all synthetic data."""
        self._generate_persons()
        self._generate_observation_periods()
        self._generate_conditions()
        self._generate_deaths()
    
    def _generate_persons(self) -> None:
        """Generate person records with realistic demographics."""
        # Age distribution: skewed toward older adults (healthcare utilizers)
        ages = np.random.gamma(shape=4, scale=12, size=self.n_patients)
        ages = np.clip(ages + 20, 0, 100)  # Shift and clip
        
        for i in range(self.n_patients):
            age = ages[i]
            birth_year = self.reference_date.year - int(age)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)
            
            gender = random.choice([GENDER_CONCEPTS["male"], GENDER_CONCEPTS["female"]])
            
            person = Person(
                person_id=i + 1,
                gender_concept_id=gender,
                year_of_birth=birth_year,
                month_of_birth=birth_month,
                day_of_birth=birth_day,
                birth_datetime=datetime(birth_year, birth_month, birth_day),
                race_concept_id=random.choice([8527, 8516, 8515, 8522]),
                ethnicity_concept_id=random.choice([38003563, 38003564]),
            )
            self.persons.append(person)
    
    def _generate_observation_periods(self) -> None:
        """Generate observation periods for each person."""
        for person in self.persons:
            # Start observation when person is at least 18 or in start_year
            birth_date = person.get_birth_date()
            earliest_start = max(
                date(self.start_year, 1, 1),
                date(birth_date.year + 18, birth_date.month, birth_date.day)
            )
            
            if earliest_start > self.reference_date:
                # Person too young for observation
                start_date = birth_date
            else:
                # Random start within valid range
                days_range = (self.reference_date - earliest_start).days
                if days_range > 365:
                    start_offset = random.randint(0, min(days_range, 365 * 3))
                    start_date = earliest_start + timedelta(days=start_offset)
                else:
                    start_date = earliest_start
            
            obs_period = ObservationPeriod(
                observation_period_id=self._obs_period_id,
                person_id=person.person_id,
                observation_period_start_date=start_date,
                observation_period_end_date=self.reference_date,
                period_type_concept_id=44814724,  # Period inferred from clinical events
            )
            self.observation_periods.append(obs_period)
            self._obs_period_id += 1
    
    def _generate_conditions(self) -> None:
        """Generate condition occurrences based on age-specific incidence."""
        for person in self.persons:
            birth_date = person.get_birth_date()
            
            # Get observation period for this person
            obs_periods = [op for op in self.observation_periods 
                          if op.person_id == person.person_id]
            if not obs_periods:
                continue
            
            obs_period = obs_periods[0]
            
            # Simulate each disease
            for disease_key, concept_set in DISEASE_CONCEPTS.items():
                if disease_key not in DISEASE_INCIDENCE_RATES:
                    continue
                
                rates = DISEASE_INCIDENCE_RATES[disease_key]
                
                # Check each year of observation for disease onset
                current_date = obs_period.observation_period_start_date
                has_disease = False
                
                while current_date <= obs_period.observation_period_end_date and not has_disease:
                    age = (current_date - birth_date).days / 365.25
                    annual_rate = get_rate_for_age(rates, age) / 1000  # Convert to probability
                    
                    # Apply rate with some randomization
                    if random.random() < annual_rate:
                        # Disease onset
                        onset_date = current_date + timedelta(days=random.randint(0, 364))
                        if onset_date <= obs_period.observation_period_end_date:
                            condition = ConditionOccurrence(
                                condition_occurrence_id=self._condition_id,
                                person_id=person.person_id,
                                condition_concept_id=concept_set.concept_ids[0],
                                condition_start_date=onset_date,
                                condition_start_datetime=datetime.combine(onset_date, datetime.min.time()),
                                condition_type_concept_id=32817,  # EHR
                            )
                            self.conditions.append(condition)
                            self._condition_id += 1
                            has_disease = True
                    
                    # Move to next year (use timedelta to handle leap years)
                    current_date = current_date + timedelta(days=365)
    
    def _generate_deaths(self) -> None:
        """Generate death records based on age-specific mortality."""
        for person in self.persons:
            birth_date = person.get_birth_date()
            
            # Get observation period
            obs_periods = [op for op in self.observation_periods 
                          if op.person_id == person.person_id]
            if not obs_periods:
                continue
            
            obs_period = obs_periods[0]
            
            # Check each year for death
            current_date = obs_period.observation_period_start_date
            
            while current_date <= obs_period.observation_period_end_date:
                age = (current_date - birth_date).days / 365.25
                annual_mortality = get_rate_for_age(MORTALITY_RATES, age) / 1000
                
                if random.random() < annual_mortality:
                    # Death occurred
                    death_date = current_date + timedelta(days=random.randint(0, 364))
                    if death_date <= obs_period.observation_period_end_date:
                        person.death_datetime = datetime.combine(death_date, datetime.min.time())
                        
                        death = Death(
                            person_id=person.person_id,
                            death_date=death_date,
                            death_datetime=person.death_datetime,
                            death_type_concept_id=32817,
                        )
                        self.deaths.append(death)
                        
                        # Update observation period end date
                        obs_period.observation_period_end_date = death_date
                        break
                
                # Move to next year (use timedelta to handle leap years)
                current_date = current_date + timedelta(days=365)
    
    def save_to_database(self, db: Database) -> dict[str, int]:
        """
        Save generated data to database.
        
        Args:
            db: Database instance to save to
            
        Returns:
            Dictionary with counts of inserted records
        """
        db.create_tables()
        
        with db.session() as session:
            session.add_all(self.persons)
            session.add_all(self.observation_periods)
            session.add_all(self.conditions)
            session.add_all(self.deaths)
        
        return {
            "persons": len(self.persons),
            "conditions": len(self.conditions),
            "observation_periods": len(self.observation_periods),
            "deaths": len(self.deaths),
        }
    
    def get_summary(self) -> dict:
        """Get summary statistics of generated data."""
        ages = []
        for person in self.persons:
            # Use stored datetime directly instead of ORM method
            if person.birth_datetime:
                birth_date = person.birth_datetime.date()
            else:
                birth_date = date(
                    person.year_of_birth,
                    person.month_of_birth or 7,
                    person.day_of_birth or 1
                )
            age = (self.reference_date - birth_date).days / 365.25
            ages.append(age)
        
        return {
            "n_patients": len(self.persons),
            "n_conditions": len(self.conditions),
            "n_deaths": len(self.deaths),
            "age_mean": np.mean(ages),
            "age_std": np.std(ages),
            "age_min": np.min(ages),
            "age_max": np.max(ages),
            "male_pct": sum(1 for p in self.persons 
                          if p.gender_concept_id == GENDER_CONCEPTS["male"]) / len(self.persons) * 100,
        }


def generate_synthetic_omop_data(
    db_path: str = "./synthetic_omop.db",
    n_patients: int = 10000,
    seed: int = 42
) -> Database:
    """
    Convenience function to generate synthetic OMOP data.
    
    Args:
        db_path: Path to SQLite database file
        n_patients: Number of patients to generate
        seed: Random seed
        
    Returns:
        Database instance with synthetic data loaded
    """
    from .database import get_sqlite_database
    
    db = get_sqlite_database(db_path)
    
    generator = SyntheticDataGenerator(n_patients=n_patients, seed=seed)
    generator.generate()
    
    # Get summary BEFORE saving to database (to avoid detached instance errors)
    summary = generator.get_summary()
    counts = generator.save_to_database(db)
    
    print(f"Generated synthetic OMOP data:")
    print(f"  Patients: {counts['persons']}")
    print(f"  Conditions: {counts['conditions']}")
    print(f"  Deaths: {counts['deaths']}")
    print(f"  Age range: {summary['age_min']:.1f} - {summary['age_max']:.1f} years")
    print(f"  Mean age: {summary['age_mean']:.1f} years")
    print(f"  Male %: {summary['male_pct']:.1f}%")
    
    return db

