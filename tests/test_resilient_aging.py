"""
Tests for the Resilient Aging package.

Run with: pytest tests/ -v
"""

import os
import tempfile
import pytest
from datetime import date, datetime

# Test fixtures and configuration
@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def populated_db(temp_db_path):
    """Create a database with synthetic test data."""
    from resilient_aging.synthetic_data import SyntheticDataGenerator
    from resilient_aging.database import get_sqlite_database
    
    db = get_sqlite_database(temp_db_path)
    
    generator = SyntheticDataGenerator(n_patients=500, seed=42)
    generator.generate()
    generator.save_to_database(db)
    
    return db


class TestSyntheticData:
    """Tests for synthetic data generation."""
    
    def test_generator_creates_persons(self, temp_db_path):
        """Test that generator creates expected number of persons."""
        from resilient_aging.synthetic_data import SyntheticDataGenerator
        from resilient_aging.database import get_sqlite_database
        
        db = get_sqlite_database(temp_db_path)
        
        generator = SyntheticDataGenerator(n_patients=100, seed=42)
        generator.generate()
        
        assert len(generator.persons) == 100
        assert len(generator.observation_periods) == 100
    
    def test_generator_creates_conditions(self, temp_db_path):
        """Test that generator creates conditions."""
        from resilient_aging.synthetic_data import SyntheticDataGenerator
        from resilient_aging.database import get_sqlite_database
        
        db = get_sqlite_database(temp_db_path)
        
        generator = SyntheticDataGenerator(n_patients=500, seed=42)
        generator.generate()
        
        # Should have some conditions (not all, not none)
        assert len(generator.conditions) > 0
        assert len(generator.conditions) < 500 * 10  # Less than 10 per person average
    
    def test_generator_save_to_database(self, temp_db_path):
        """Test saving generated data to database."""
        from resilient_aging.synthetic_data import SyntheticDataGenerator
        from resilient_aging.database import get_sqlite_database
        
        db = get_sqlite_database(temp_db_path)
        
        generator = SyntheticDataGenerator(n_patients=100, seed=42)
        generator.generate()
        counts = generator.save_to_database(db)
        
        assert counts['persons'] == 100
        assert counts['observation_periods'] == 100
        
        # Verify data is in database
        db_counts = db.get_table_counts()
        assert db_counts['person'] == 100
    
    def test_reproducible_with_seed(self, temp_db_path):
        """Test that same seed produces same data."""
        from resilient_aging.synthetic_data import SyntheticDataGenerator
        
        gen1 = SyntheticDataGenerator(n_patients=50, seed=123)
        gen1.generate()
        
        gen2 = SyntheticDataGenerator(n_patients=50, seed=123)
        gen2.generate()
        
        # Same number of conditions
        assert len(gen1.conditions) == len(gen2.conditions)
        
        # Same persons
        assert gen1.persons[0].year_of_birth == gen2.persons[0].year_of_birth


class TestPrevalence:
    """Tests for prevalence calculations."""
    
    def test_calculate_age_at_diagnosis(self, populated_db):
        """Test age at diagnosis calculation."""
        from resilient_aging.prevalence import calculate_age_at_diagnosis
        from resilient_aging.concept_sets import DISEASE_CONCEPTS
        
        concept_ids = DISEASE_CONCEPTS['type2_diabetes'].concept_ids
        
        with populated_db.session() as session:
            df = calculate_age_at_diagnosis(session, concept_ids)
        
        assert len(df) > 0
        assert 'person_id' in df.columns
        assert 'age_at_diagnosis' in df.columns
        assert 'current_age' in df.columns
        assert 'has_condition' in df.columns
    
    def test_calculate_cumulative_incidence(self, populated_db):
        """Test cumulative incidence calculation."""
        from resilient_aging.prevalence import calculate_cumulative_incidence
        from resilient_aging.concept_sets import DISEASE_CONCEPTS
        
        concept_ids = DISEASE_CONCEPTS['type2_diabetes'].concept_ids
        
        with populated_db.session() as session:
            df = calculate_cumulative_incidence(session, concept_ids)
        
        assert len(df) > 0
        assert 'age' in df.columns
        assert 'cumulative_incidence' in df.columns
        
        # Cumulative incidence should increase with age
        assert df['cumulative_incidence'].iloc[-1] >= df['cumulative_incidence'].iloc[0]
    
    def test_disease_free_survival(self, populated_db):
        """Test disease-free survival calculation."""
        from resilient_aging.prevalence import calculate_disease_free_survival
        from resilient_aging.concept_sets import DISEASE_CONCEPTS
        
        concept_ids = DISEASE_CONCEPTS['hypertension'].concept_ids
        
        with populated_db.session() as session:
            df = calculate_disease_free_survival(session, concept_ids)
        
        assert 'disease_free_survival' in df.columns
        
        # Disease-free survival should decrease with age
        assert df['disease_free_survival'].iloc[0] >= df['disease_free_survival'].iloc[-1]


class TestResilientAger:
    """Tests for resilient ager classification."""
    
    def test_get_population_thresholds(self, populated_db):
        """Test population threshold calculation."""
        from resilient_aging.resilient_ager import get_population_thresholds
        
        with populated_db.session() as session:
            thresholds = get_population_thresholds(session, 'type2_diabetes')
        
        assert thresholds.n_total > 0
        assert thresholds.prevalence >= 0
        assert thresholds.prevalence <= 1
    
    def test_classify_resilient_agers(self, populated_db):
        """Test resilient ager classification."""
        from resilient_aging.resilient_ager import classify_resilient_agers
        
        with populated_db.session() as session:
            df = classify_resilient_agers(session, 'type2_diabetes')
        
        assert len(df) > 0
        assert 'is_resilient' in df.columns
        assert 'classification' in df.columns
        
        # Check valid classifications
        valid_classes = ['resilient_ager', 'affected', 'late_onset', 
                        'disease_free_not_threshold', 'too_young']
        assert all(c in valid_classes for c in df['classification'].unique())
    
    def test_create_cohort(self, populated_db):
        """Test cohort creation."""
        from resilient_aging.resilient_ager import create_cohort
        
        with populated_db.session() as session:
            resilient = create_cohort(session, 'type2_diabetes', 'resilient_ager')
            affected = create_cohort(session, 'type2_diabetes', 'affected')
        
        # All resilient agers should be disease-free
        assert all(resilient['has_condition'] == False) if len(resilient) > 0 else True
        
        # All affected should have condition
        assert all(affected['has_condition'] == True) if len(affected) > 0 else True
    
    def test_compare_cohorts(self, populated_db):
        """Test cohort comparison."""
        from resilient_aging.resilient_ager import compare_cohorts
        
        with populated_db.session() as session:
            comparison = compare_cohorts(session, 'type2_diabetes')
        
        assert 'n_resilient' in comparison
        assert 'n_affected' in comparison
        assert 'pct_resilient' in comparison
        
        # Percentages should be valid
        assert comparison['pct_resilient'] >= 0
        assert comparison['pct_resilient'] <= 100


class TestDatabase:
    """Tests for database operations."""
    
    def test_database_connection(self, temp_db_path):
        """Test database connection."""
        from resilient_aging.database import get_sqlite_database
        
        db = get_sqlite_database(temp_db_path)
        assert db.is_connected()
    
    def test_create_tables(self, temp_db_path):
        """Test table creation."""
        from resilient_aging.database import get_sqlite_database
        
        db = get_sqlite_database(temp_db_path)
        db.create_tables()
        
        # Check tables exist
        counts = db.get_table_counts()
        assert 'person' in counts


class TestConceptSets:
    """Tests for concept set definitions."""
    
    def test_disease_concepts_defined(self):
        """Test that disease concepts are properly defined."""
        from resilient_aging.concept_sets import DISEASE_CONCEPTS
        
        assert 'type2_diabetes' in DISEASE_CONCEPTS
        assert 'alzheimer' in DISEASE_CONCEPTS
        assert 'coronary_artery_disease' in DISEASE_CONCEPTS
    
    def test_concept_set_has_ids(self):
        """Test that concept sets have concept IDs."""
        from resilient_aging.concept_sets import DISEASE_CONCEPTS
        
        for key, concept_set in DISEASE_CONCEPTS.items():
            assert len(concept_set.concept_ids) > 0, f"{key} has no concept IDs"
    
    def test_list_available_diseases(self):
        """Test listing available diseases."""
        from resilient_aging.concept_sets import list_available_diseases
        
        diseases = list_available_diseases()
        assert len(diseases) > 0
        assert 'type2_diabetes' in diseases


class TestIntegration:
    """Integration tests for end-to-end workflow."""
    
    def test_full_workflow(self, temp_db_path):
        """Test complete workflow from data generation to analysis."""
        from resilient_aging.synthetic_data import generate_synthetic_omop_data
        from resilient_aging.resilient_ager import (
            get_population_thresholds,
            classify_resilient_agers,
            compare_cohorts,
        )
        
        # Generate data
        db = generate_synthetic_omop_data(temp_db_path, n_patients=200, seed=42)
        
        # Run analysis
        with db.session() as session:
            # Get thresholds
            thresholds = get_population_thresholds(session, 'hypertension')
            assert thresholds.n_total == 200
            
            # Classify
            df = classify_resilient_agers(session, 'hypertension')
            assert len(df) == 200
            
            # Compare
            comparison = compare_cohorts(session, 'hypertension')
            assert comparison['total_eligible'] <= 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
