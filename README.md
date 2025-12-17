# Resilient Aging Algorithm

A Python package for identifying **resilient agers** from OMOP Common Data Model (CDM) data. Resilient agers are individuals who remain disease-free beyond population-expected age thresholds.

## Overview

This package implements the Resilient Aging phenotype identification algorithm:

1. **Calculate age-specific disease incidence** - Determines cumulative incidence curves for target diseases
2. **Identify population thresholds** - Finds the ages by which 50%, 75%, and 90% of affected individuals are diagnosed
3. **Classify resilient agers** - Identifies individuals who remain disease-free beyond the 75th percentile threshold
4. **Generate cohorts** - Creates cohorts for downstream analysis

## Installation

```bash
cd /path/to/resilient_aging
pip install -e ".[test]"
```

## Quick Start

### 1. Generate Synthetic Data (for testing)

```bash
# Generate 10,000 synthetic patients
resilient-aging generate-data --patients 10000 --output ./synthetic_omop.db
```

### 2. Run Analysis

```bash
# Analyze a specific disease
resilient-aging run-analysis --database ./synthetic_omop.db --disease type2_diabetes

# List available diseases
resilient-aging list-diseases
```

### 3. Export Cohort

```bash
# Export resilient agers to CSV
resilient-aging export-cohort --database ./synthetic_omop.db \
    --disease type2_diabetes \
    --output ./resilient_cohort.csv
```

### 4. Generate Visualizations

```bash
resilient-aging visualize --database ./synthetic_omop.db --output ./plots
```

## Python API

```python
from resilient_aging import Database, get_sqlite_database
from resilient_aging.resilient_ager import (
    get_population_thresholds,
    classify_resilient_agers,
    compare_cohorts,
)

# Connect to database
db = get_sqlite_database("./synthetic_omop.db")

with db.session() as session:
    # Get population thresholds
    thresholds = get_population_thresholds(session, "type2_diabetes")
    print(f"75th percentile onset age: {thresholds.percentile_75_onset_age:.1f}")
    
    # Classify all individuals
    df = classify_resilient_agers(session, "type2_diabetes")
    resilient = df[df['is_resilient'] == True]
    print(f"Resilient agers: {len(resilient)}")
    
    # Compare cohorts
    comparison = compare_cohorts(session, "type2_diabetes")
    print(f"Resilient: {comparison['pct_resilient']:.1f}%")
```

## Using with Real OMOP Database

### PostgreSQL Connection

Create a `config.yaml` file:

```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  name: omop_cdm
  user: your_username
  password: your_password
```

Then:

```python
from resilient_aging import create_engine_from_config

db = create_engine_from_config("./config.yaml")
```

### Direct Connection

```python
from resilient_aging import Database

db = Database("postgresql://user:password@localhost:5432/omop_cdm")
```

## Available Diseases

| Key | Disease |
|-----|---------|
| `type2_diabetes` | Type 2 Diabetes Mellitus |
| `alzheimer` | Alzheimer's Disease |
| `coronary_artery_disease` | Coronary Artery Disease |
| `atrial_fibrillation` | Atrial Fibrillation |
| `heart_failure` | Heart Failure |
| `copd` | COPD |
| `hypertension` | Essential Hypertension |
| `stroke` | Stroke |
| `cancer_breast` | Breast Cancer |
| `cancer_prostate` | Prostate Cancer |
| `cancer_colorectal` | Colorectal Cancer |
| `osteoporosis` | Osteoporosis |
| `chronic_kidney_disease` | Chronic Kidney Disease |
| `parkinson` | Parkinson's Disease |

## Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_resilient_aging.py -v
```

## Project Structure

```
resilient_aging/
├── __init__.py          # Package exports
├── omop_schema.py       # OMOP CDM SQLAlchemy models
├── database.py          # Database connectivity
├── concept_sets.py      # Disease concept definitions
├── synthetic_data.py    # Synthetic data generator
├── prevalence.py        # Prevalence/incidence calculations
├── resilient_ager.py    # Core classification algorithm
└── cli.py               # Command-line interface
```

## Algorithm Details

The algorithm identifies resilient agers through these steps:

1. **Extract diagnosis data**: Query OMOP `condition_occurrence` table for target disease concepts
2. **Calculate age at diagnosis**: For each person, determine their age at first diagnosis
3. **Compute population thresholds**: Among those with the disease, find the 75th percentile onset age
4. **Classify individuals**:
   - **Resilient Ager**: Disease-free AND current age >= 75th percentile threshold AND age >= 60
   - **Affected**: Has the condition
   - **Disease-free (not threshold)**: Disease-free but hasn't reached threshold age
   - **Too young**: Under minimum age for classification (default: 60)

## License

MIT License
