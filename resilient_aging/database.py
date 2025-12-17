"""
Database connectivity layer for OMOP CDM databases.

Supports both SQLite (for testing/synthetic data) and PostgreSQL
(for production OMOP databases).
"""

import os
from typing import Optional, Generator
from contextlib import contextmanager

import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .omop_schema import Base


class Database:
    """
    Database connection manager for OMOP CDM.
    
    Provides connection pooling, session management, and schema creation.
    
    Examples:
        # SQLite for testing
        db = Database("sqlite:///test_data.db")
        
        # PostgreSQL for production
        db = Database("postgresql://user:pass@localhost/omop")
        
        # Using context manager
        with db.session() as session:
            persons = session.query(Person).all()
    """
    
    def __init__(self, connection_string: str, echo: bool = False):
        """
        Initialize database connection.
        
        Args:
            connection_string: SQLAlchemy database URL
            echo: If True, log all SQL statements
        """
        self.connection_string = connection_string
        self.engine = create_engine(connection_string, echo=echo)
        self._session_factory = sessionmaker(bind=self.engine)
    
    def create_tables(self) -> None:
        """Create all OMOP CDM tables if they don't exist."""
        Base.metadata.create_all(self.engine)
    
    def drop_tables(self) -> None:
        """Drop all OMOP CDM tables. USE WITH CAUTION."""
        Base.metadata.drop_all(self.engine)
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Yields:
            Session: SQLAlchemy session
            
        Example:
            with db.session() as session:
                person = session.query(Person).first()
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute_sql(self, sql: str) -> list:
        """
        Execute raw SQL and return results.
        
        Args:
            sql: SQL query string
            
        Returns:
            List of result rows
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return result.fetchall()
    
    def get_table_counts(self) -> dict[str, int]:
        """Get row counts for all OMOP tables."""
        counts = {}
        tables = ["person", "condition_occurrence", "observation_period", "death"]
        for table in tables:
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    counts[table] = result.scalar()
            except Exception:
                counts[table] = 0
        return counts
    
    def is_connected(self) -> bool:
        """Test if database connection is working."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


def create_engine_from_config(config_path: str) -> Database:
    """
    Create Database instance from YAML config file.
    
    Args:
        config_path: Path to config.yaml file
        
    Returns:
        Configured Database instance
        
    Config file format:
        database:
          type: sqlite  # or postgresql
          path: ./data.db  # for sqlite
          host: localhost  # for postgresql
          port: 5432
          name: omop
          user: username
          password: password
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config.get('database', {})
    db_type = db_config.get('type', 'sqlite')
    
    if db_type == 'sqlite':
        path = db_config.get('path', './omop_data.db')
        connection_string = f"sqlite:///{path}"
    elif db_type == 'postgresql':
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        name = db_config.get('name', 'omop')
        user = db_config.get('user', 'postgres')
        password = db_config.get('password', '')
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    return Database(connection_string)


def get_sqlite_database(path: str = "./omop_data.db") -> Database:
    """
    Convenience function to create SQLite database.
    
    Args:
        path: Path to SQLite database file
        
    Returns:
        Database instance connected to SQLite
    """
    return Database(f"sqlite:///{path}")
