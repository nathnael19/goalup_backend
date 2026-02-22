"""
Script to reset the GoalUp database.
Drops all tables and recreates them.
"""
from sqlmodel import SQLModel
from app.core.database import engine
# Import all models to ensure they are registered with SQLModel.metadata
from app.models.user import User
from app.models.match import Match
from app.models.tournament import Tournament
from app.models.competition import Competition
from app.models.team import Team
from app.models.player import Player
from app.models.goal import Goal
from app.models.card import Card
from app.models.substitution import Substitution
from app.models.lineup import Lineup
from app.models.news import News
from app.models.notification import Notification
from app.models.audit_log import AuditLog

def reset_database():
    print("⚠️  Warning: This will delete ALL data in the database.")
    # In a scripted environment, we might want to skip the confirmation if needed
    # but for safety, we list the action.
    
    print("Dropping all tables...")
    SQLModel.metadata.drop_all(engine)
    
    print("Recreating all tables...")
    SQLModel.metadata.create_all(engine)
    
    print("✅ Database reset complete!")

if __name__ == "__main__":
    reset_database()
