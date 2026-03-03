"""
Database Connection Module
===========================

Handles PostgreSQL connection for FastAPI application.
Uses SQLAlchemy for database operations.

Author: ObRail Europe
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Loads environment variables
load_dotenv()

# Builds database URL from environment variables
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f"postgresql://{os.getenv('POSTGRES_USER', 'obrail_user')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5433')}/"
    f"{os.getenv('POSTGRES_DB', 'obrail_db')}"
)

DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Creates SQLAlchemy engine
# This manages all database connections
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Creates session factory
# Sessions are used to query the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency function to get database session.
    
    Used in FastAPI endpoints like:
    @app.get("/routes")
    def get_routes(db: Session = Depends(get_db)):
        ...
    
    Automatically closes connection after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()