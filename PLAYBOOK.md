# Resilient Aging Algorithm Playbook

A comprehensive guide to identifying individuals who remain disease-free longer than expected using OMOP CDM data.

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start (5 minutes)](#quick-start)
4. [CLI Reference](#cli-reference)
5. [Python API Guide](#python-api-guide)
6. [Using Real OMOP Data](#using-real-omop-data)
7. [Interpreting Results](#interpreting-results)
8. [Available Diseases](#available-diseases)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### What is a Resilient Ager?

A **resilient ager** is an individual who remains free of a specific age-related disease beyond the age at which 75% of affected individuals in the population have been diagnosed.

```
┌─────────────────────────────────────────────────────────────────┐
│  Example: Type 2 Diabetes                                       │
│                                                                 │
│  75th percentile onset age = 79.1 years                         │
│                                                                 │
│  Person A: Age 85, no diabetes → RESILIENT AGER ✅              │
│  Person B: Age 70, no diabetes → Not yet threshold (too young) │
│  Person C: Age 90, has diabetes → Affected (not resilient)     │
└─────────────────────────────────────────────────────────────────┘
```

### Algorithm Summary

1. Query all condition occurrences for a target disease
2. Calculate age at first diagnosis for each person
3. Compute the 75th percentile onset age (threshold)
4. Classify disease-free individuals above threshold as resilient agers

---

## Installation

### Prerequisites

- Python 3.9+
- pip package manager

### Install Package

```bash
cd /Users/xjiang2/Dropbox/cursor_projects/mac/resilient_aging
pip install -e ".[test]"
```

### Verify Installation

```bash
resilient-aging --version
# Output: resilient-aging, version 0.1.0

resilient-aging list-diseases
# Shows all 14 available diseases
```

---

## Quick Start

### Step 1: Generate Synthetic Data

```bash
resilient-aging generate-data --patients 10000 --output ./my_data.db
```

**Output:**
```
Generated synthetic OMOP data:
  Patients: 10,000
  Conditions: ~9,000
  Deaths: ~2,500
  Age range: 20 - 100 years
```

### Step 2: Run Analysis

```bash
resilient-aging run-analysis --database ./my_data.db --disease type2_diabetes
```

**Output:**
```
Analyzing: type2_diabetes
--------------------------------------------------
Total population: 10,000
Affected individuals: 1,100 (11.0%)
Median onset age: 67.6 years
75th percentile onset age: 79.1 years

Cohort Comparison (age >= 60.0):
--------------------------------------------------
Total eligible: 6,156
Resilient agers: 2,516 (40.9%)
Affected: 916 (14.9%)
Average resilience score: 14.9 years beyond threshold
```

### Step 3: Export Results

```bash
# Export resilient agers to CSV
resilient-aging export-cohort --database ./my_data.db \
    --disease type2_diabetes \
    --output ./resilient_t2d.csv
```

### Step 4: Generate Visualizations

```bash
resilient-aging visualize --database ./my_data.db --output ./plots
```

Creates 4 plots in `./plots/`:
- `cumulative_incidence.png` - Disease onset curves by age
- `disease_free_survival.png` - Probability of remaining disease-free
- `resilient_agers_[disease].png` - Classification breakdown
- `multi_disease_comparison.png` - Cross-disease comparison

---

## CLI Reference

### `generate-data`

Generate synthetic OMOP data for testing.

```bash
resilient-aging generate-data [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--patients, -n` | 10000 | Number of patients |
| `--output, -o` | ./synthetic_omop.db | Database file path |
| `--seed, -s` | 42 | Random seed |

### `run-analysis`

Analyze resilient agers for a specific disease.

```bash
resilient-aging run-analysis [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--database, -d` | Yes | Path to SQLite/OMOP database |
| `--disease, -D` | Yes | Disease key (e.g., type2_diabetes) |
| `--min-age` | 60.0 | Minimum age for classification |
| `--threshold` | 75.0 | Percentile threshold |

### `export-cohort`

Export cohort members to CSV.

```bash
resilient-aging export-cohort [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--database, -d` | Yes | Database path |
| `--disease, -D` | Yes | Disease key |
| `--output, -o` | ./resilient_cohort.csv | Output CSV path |
| `--cohort-type, -t` | resilient_ager | One of: resilient_ager, affected, typical |

### `visualize`

Generate visualization plots.

```bash
resilient-aging visualize [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--database, -d` | Yes | Database path |
| `--output, -o` | ./plots | Output directory |
| `--disease, -D` | None | Specific disease (default: all) |

### `list-diseases`

List all available disease concept sets.

```bash
resilient-aging list-diseases
```

---

## Python API Guide

### Basic Usage

```python
from resilient_aging import Database, get_sqlite_database
from resilient_aging.resilient_ager import (
    get_population_thresholds,
    classify_resilient_agers,
    compare_cohorts,
    create_cohort,
)

# Connect to database
db = get_sqlite_database("./my_data.db")

with db.session() as session:
    # Get population statistics
    thresholds = get_population_thresholds(session, "type2_diabetes")
    print(f"Threshold age: {thresholds.percentile_75_onset_age:.1f}")
    print(f"Prevalence: {thresholds.prevalence * 100:.1f}%")
    
    # Classify all individuals
    df = classify_resilient_agers(session, "type2_diabetes")
    resilient = df[df['is_resilient'] == True]
    print(f"Resilient agers: {len(resilient)}")
    
    # Get comparison statistics
    comparison = compare_cohorts(session, "type2_diabetes")
    print(f"Resilient: {comparison['pct_resilient']:.1f}%")
```

### Generate Synthetic Data Programmatically

```python
from resilient_aging.synthetic_data import SyntheticDataGenerator, generate_synthetic_omop_data

# Quick method
db = generate_synthetic_omop_data("./test.db", n_patients=5000, seed=42)

# Detailed control
generator = SyntheticDataGenerator(
    n_patients=10000,
    start_year=2010,
    end_year=2023,
    seed=42
)
generator.generate()
summary = generator.get_summary()
print(f"Mean age: {summary['age_mean']:.1f}")
generator.save_to_database(db)
```

### Multi-Disease Analysis

```python
from resilient_aging.resilient_ager import run_multi_disease_analysis

with db.session() as session:
    results = run_multi_disease_analysis(
        session,
        disease_keys=["type2_diabetes", "alzheimer", "hypertension"],
        min_age=60.0
    )
    print(results[['disease_key', 'pct_resilient', 'threshold_age']])
```

### Cumulative Incidence Curves

```python
from resilient_aging.prevalence import (
    calculate_cumulative_incidence,
    calculate_disease_free_survival,
)
from resilient_aging.concept_sets import DISEASE_CONCEPTS

with db.session() as session:
    concept_ids = DISEASE_CONCEPTS['alzheimer'].concept_ids
    
    # Get cumulative incidence by age
    cum_inc = calculate_cumulative_incidence(session, concept_ids)
    print(cum_inc[['age', 'cumulative_incidence_pct']].head(20))
    
    # Get disease-free survival
    dfs = calculate_disease_free_survival(session, concept_ids)
    print(dfs[['age', 'disease_free_pct']].head(20))
```

---

## Using Real OMOP Data

### PostgreSQL Connection

Create `config.yaml`:

```yaml
database:
  type: postgresql
  host: your-database-host
  port: 5432
  name: omop_cdm
  user: your_username
  password: your_password
```

```python
from resilient_aging import create_engine_from_config

db = create_engine_from_config("./config.yaml")
```

### Direct Connection String

```python
from resilient_aging import Database

# PostgreSQL
db = Database("postgresql://user:pass@host:5432/omop_cdm")

# SQLite
db = Database("sqlite:///path/to/database.db")
```

### Validating Concept Sets

Before running on real data, verify concept IDs match your OMOP vocabulary:

```python
from resilient_aging.concept_sets import DISEASE_CONCEPTS

# Check concept IDs
for disease, concept_set in DISEASE_CONCEPTS.items():
    print(f"{disease}: {concept_set.concept_ids}")
```

> [!WARNING]
> The default concept IDs are placeholder values. For production use, validate against your OMOP vocabulary tables.

---

## Interpreting Results

### Key Metrics

| Metric | Description |
|--------|-------------|
| **75th Percentile Onset Age** | Age by which 75% of affected individuals are diagnosed |
| **Resilience Score** | Years beyond the threshold that a person has remained disease-free |
| **Prevalence** | Proportion of population with the condition |

### Classification Categories

| Classification | Meaning |
|----------------|---------|
| `resilient_ager` | Disease-free, age ≥ threshold, age ≥ 60 |
| `affected` | Has the disease |
| `late_onset` | Has disease, but diagnosed after threshold |
| `disease_free_not_threshold` | Disease-free but hasn't reached threshold age |
| `too_young` | Under minimum age for classification |

### Sample Interpretation

```
Disease: Type 2 Diabetes
Threshold age: 79.1 years
Resilient agers: 1,258 (40.9%)
Average resilience score: 14.9 years

→ 40.9% of individuals over 60 remained diabetes-free
  beyond the age when 75% of diabetics are typically diagnosed.
→ On average, they've been disease-free 14.9 years longer
  than the population threshold.
```

---

## Available Diseases

| Key | Disease | SNOMED Code |
|-----|---------|-------------|
| `type2_diabetes` | Type 2 Diabetes Mellitus | 44054006 |
| `alzheimer` | Alzheimer's Disease | 26929004 |
| `coronary_artery_disease` | Coronary Artery Disease | 53741008 |
| `atrial_fibrillation` | Atrial Fibrillation | 49436004 |
| `heart_failure` | Heart Failure | 84114007 |
| `copd` | COPD | 13645005 |
| `hypertension` | Essential Hypertension | 59621000 |
| `stroke` | Stroke | 230690007 |
| `cancer_breast` | Breast Cancer | 254837009 |
| `cancer_prostate` | Prostate Cancer | 399068003 |
| `cancer_colorectal` | Colorectal Cancer | 363406005 |
| `osteoporosis` | Osteoporosis | 64859006 |
| `chronic_kidney_disease` | Chronic Kidney Disease | 709044004 |
| `parkinson` | Parkinson's Disease | 49049000 |

---

## Troubleshooting

### Common Issues

**"Unknown disease key"**
```bash
resilient-aging list-diseases  # See available keys
```

**Database connection failed**
```python
db = get_sqlite_database("./data.db")
print(db.is_connected())  # Should return True
```

**Empty results**
- Check that synthetic data was generated: `db.get_table_counts()`
- Verify disease has conditions in the data

**Import errors**
```bash
pip install -e ".[test]"  # Reinstall package
```

---

## File Locations

| File | Purpose |
|------|---------|
| `/Users/xjiang2/Dropbox/cursor_projects/mac/resilient_aging/` | Package root |
| `./resilient_aging/cli.py` | CLI implementation |
| `./resilient_aging/resilient_ager.py` | Core algorithm |
| `./tests/test_resilient_aging.py` | Test suite |
| `./config.yaml` | Database configuration template |
| `./README.md` | Quick reference |
