"""
Command-line interface for the Resilient Aging algorithm.

Usage:
    resilient-aging generate-data --patients 10000 --output ./data.db
    resilient-aging run-analysis --database ./data.db --disease type2_diabetes
    resilient-aging export-cohort --database ./data.db --disease type2_diabetes
    resilient-aging visualize --database ./data.db --output ./plots
"""

import click
import os
import sys
from datetime import date

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Resilient Aging - Identify resilient agers from OMOP CDM data."""
    pass


@main.command()
@click.option('--patients', '-n', default=10000, help='Number of patients to generate')
@click.option('--output', '-o', default='./synthetic_omop.db', help='Output database path')
@click.option('--seed', '-s', default=42, help='Random seed for reproducibility')
def generate_data(patients: int, output: str, seed: int):
    """Generate synthetic OMOP data for testing."""
    from .synthetic_data import generate_synthetic_omop_data
    
    click.echo(f"Generating synthetic OMOP data with {patients} patients...")
    db = generate_synthetic_omop_data(db_path=output, n_patients=patients, seed=seed)
    click.echo(f"Data saved to: {output}")
    
    # Show summary
    counts = db.get_table_counts()
    click.echo("\nDatabase summary:")
    for table, count in counts.items():
        click.echo(f"  {table}: {count:,} records")


@main.command()
@click.option('--database', '-d', required=True, help='Path to OMOP database')
@click.option('--disease', '-D', required=True, help='Disease key (e.g., type2_diabetes)')
@click.option('--min-age', default=60.0, help='Minimum age for resilience classification')
@click.option('--threshold', default=75.0, help='Percentile threshold (default: 75)')
def run_analysis(database: str, disease: str, min_age: float, threshold: float):
    """Run resilient aging analysis for a specific disease."""
    from .database import get_sqlite_database
    from .resilient_ager import get_population_thresholds, compare_cohorts
    from .concept_sets import list_available_diseases
    
    available = list_available_diseases()
    if disease not in available:
        click.echo(f"Error: Unknown disease '{disease}'")
        click.echo(f"Available diseases: {', '.join(available)}")
        return
    
    click.echo(f"Connecting to database: {database}")
    db = get_sqlite_database(database)
    
    with db.session() as session:
        # Get population thresholds
        click.echo(f"\nAnalyzing: {disease}")
        click.echo("-" * 50)
        
        thresholds = get_population_thresholds(session, disease)
        click.echo(f"Total population: {thresholds.n_total:,}")
        click.echo(f"Affected individuals: {thresholds.n_affected:,} ({thresholds.prevalence*100:.1f}%)")
        click.echo(f"Median onset age: {thresholds.median_onset_age:.1f} years" if thresholds.median_onset_age else "Median onset age: N/A")
        click.echo(f"75th percentile onset age: {thresholds.percentile_75_onset_age:.1f} years" if thresholds.percentile_75_onset_age else "75th percentile: N/A")
        
        # Compare cohorts
        comparison = compare_cohorts(session, disease, min_age=min_age)
        
        click.echo(f"\nCohort Comparison (age >= {min_age}):")
        click.echo("-" * 50)
        click.echo(f"Total eligible: {comparison['total_eligible']:,}")
        click.echo(f"Resilient agers: {comparison['n_resilient']:,} ({comparison['pct_resilient']:.1f}%)")
        click.echo(f"Affected: {comparison['n_affected']:,} ({comparison['pct_affected']:.1f}%)")
        click.echo(f"Disease-free (not threshold): {comparison['n_typical']:,}")
        
        if comparison['avg_age_resilient']:
            click.echo(f"\nAverage age of resilient agers: {comparison['avg_age_resilient']:.1f} years")
        if comparison['avg_resilience_score']:
            click.echo(f"Average resilience score: {comparison['avg_resilience_score']:.1f} years beyond threshold")


@main.command()
@click.option('--database', '-d', required=True, help='Path to OMOP database')
@click.option('--disease', '-D', required=True, help='Disease key')
@click.option('--output', '-o', default='./resilient_cohort.csv', help='Output CSV path')
@click.option('--cohort-type', '-t', default='resilient_ager', 
              type=click.Choice(['resilient_ager', 'affected', 'typical']),
              help='Type of cohort to export')
def export_cohort(database: str, disease: str, output: str, cohort_type: str):
    """Export cohort to CSV file."""
    from .database import get_sqlite_database
    from .resilient_ager import create_cohort
    
    click.echo(f"Connecting to database: {database}")
    db = get_sqlite_database(database)
    
    with db.session() as session:
        cohort = create_cohort(session, disease, cohort_type=cohort_type)
        
        cohort.to_csv(output, index=False)
        click.echo(f"Exported {len(cohort)} {cohort_type} individuals to: {output}")


@main.command()
@click.option('--database', '-d', required=True, help='Path to OMOP database')
@click.option('--output', '-o', default='./plots', help='Output directory for plots')
@click.option('--disease', '-D', default=None, help='Specific disease (default: all)')
def visualize(database: str, output: str, disease: str):
    """Generate visualization plots."""
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    from .database import get_sqlite_database
    from .prevalence import calculate_cumulative_incidence, calculate_disease_free_survival
    from .resilient_ager import classify_resilient_agers, run_multi_disease_analysis
    from .concept_sets import DISEASE_CONCEPTS, list_available_diseases
    
    os.makedirs(output, exist_ok=True)
    
    click.echo(f"Connecting to database: {database}")
    db = get_sqlite_database(database)
    
    diseases = [disease] if disease else list_available_diseases()[:6]  # Limit to 6 for plotting
    
    with db.session() as session:
        # Plot 1: Cumulative incidence curves
        fig, ax = plt.subplots(figsize=(12, 8))
        for disease_key in diseases:
            try:
                concept_ids = DISEASE_CONCEPTS[disease_key].concept_ids
                cum_inc = calculate_cumulative_incidence(session, concept_ids)
                ax.plot(cum_inc['age'], cum_inc['cumulative_incidence_pct'], 
                       label=DISEASE_CONCEPTS[disease_key].name, linewidth=2)
            except Exception as e:
                click.echo(f"Warning: Could not plot {disease_key}: {e}")
        
        ax.set_xlabel('Age (years)', fontsize=12)
        ax.set_ylabel('Cumulative Incidence (%)', fontsize=12)
        ax.set_title('Cumulative Disease Incidence by Age', fontsize=14)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 100)
        
        plot_path = os.path.join(output, 'cumulative_incidence.png')
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        click.echo(f"Saved: {plot_path}")
        
        # Plot 2: Disease-free survival
        fig, ax = plt.subplots(figsize=(12, 8))
        for disease_key in diseases:
            try:
                concept_ids = DISEASE_CONCEPTS[disease_key].concept_ids
                dfs = calculate_disease_free_survival(session, concept_ids)
                ax.plot(dfs['age'], dfs['disease_free_pct'], 
                       label=DISEASE_CONCEPTS[disease_key].name, linewidth=2)
            except Exception:
                pass
        
        ax.set_xlabel('Age (years)', fontsize=12)
        ax.set_ylabel('Disease-Free Survival (%)', fontsize=12)
        ax.set_title('Disease-Free Survival by Age', fontsize=14)
        ax.legend(loc='lower left')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        
        plot_path = os.path.join(output, 'disease_free_survival.png')
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        click.echo(f"Saved: {plot_path}")
        
        # Plot 3: Resilient ager distribution for first disease
        if diseases:
            disease_key = diseases[0]
            df = classify_resilient_agers(session, disease_key)
            
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            
            # Age distribution by classification
            sns.histplot(data=df, x='current_age', hue='classification', 
                        ax=axes[0], bins=30, alpha=0.7)
            axes[0].set_xlabel('Current Age (years)')
            axes[0].set_ylabel('Count')
            axes[0].set_title(f'Age Distribution by Classification\n({DISEASE_CONCEPTS[disease_key].name})')
            
            # Pie chart of classifications
            class_counts = df['classification'].value_counts()
            axes[1].pie(class_counts.values, labels=class_counts.index, autopct='%1.1f%%')
            axes[1].set_title('Classification Distribution')
            
            plt.tight_layout()
            plot_path = os.path.join(output, f'resilient_agers_{disease_key}.png')
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            click.echo(f"Saved: {plot_path}")
        
        # Plot 4: Multi-disease comparison
        multi_results = run_multi_disease_analysis(session)
        if len(multi_results) > 0:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            x = range(len(multi_results))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], multi_results['pct_resilient'], 
                   width, label='Resilient Agers', color='green', alpha=0.7)
            ax.bar([i + width/2 for i in x], multi_results['pct_affected'], 
                   width, label='Affected', color='red', alpha=0.7)
            
            ax.set_xlabel('Disease')
            ax.set_ylabel('Percentage of Population (%)')
            ax.set_title('Resilient Agers vs Affected by Disease (Age >= 60)')
            ax.set_xticks(x)
            ax.set_xticklabels(multi_results['disease_key'], rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            plot_path = os.path.join(output, 'multi_disease_comparison.png')
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            click.echo(f"Saved: {plot_path}")
    
    click.echo(f"\nAll plots saved to: {output}")


@main.command()
def list_diseases():
    """List available disease concept sets."""
    from .concept_sets import DISEASE_CONCEPTS
    
    click.echo("Available disease concept sets:")
    click.echo("-" * 50)
    for key, concept_set in DISEASE_CONCEPTS.items():
        click.echo(f"  {key}: {concept_set.name}")
        click.echo(f"    Concept IDs: {concept_set.concept_ids}")
    click.echo("-" * 50)
    click.echo(f"Total: {len(DISEASE_CONCEPTS)} diseases")


if __name__ == '__main__':
    main()
