"""
Script to create an admin user for the GoalUp backend.
Run this script to create the initial admin user.
"""
import sys
from sqlmodel import Session, select
from app.core.database import engine
from app.core.security import get_password_hash
from app.models.user import User

def create_admin_user(email: str, password: str, full_name: str):
    """Create an admin user."""
    with Session(engine) as session:
        # Check if user already exists
        statement = select(User).where(User.email == email)
        existing_user = session.exec(statement).first()
        
        if existing_user:
            print(f"User with email {email} already exists!")
            return
        
        # Create new admin user
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.full_name}")
        print(f"   ID: {user.id}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <email> <password> <full_name>")
        print('Example: python create_admin.py admin@goalup.com admin123 "Admin User"')
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3]
    
    create_admin_user(email, password, full_name)
