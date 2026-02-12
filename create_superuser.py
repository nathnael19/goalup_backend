import sys
import os

# Add the current directory to sys.path to allow imports from app
sys.path.append(os.getcwd())

from sqlmodel import Session, select
from app.core.database import engine, create_db_and_tables
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def create_superuser(email, password):
    # Ensure tables exist
    create_db_and_tables()
    
    with Session(engine) as session:
        # Check if user already exists
        statement = select(User).where(User.email == email)
        existing_user = session.exec(statement).first()
        
        if existing_user:
            print(f"User with email {email} already exists.")
            # Optionally update to superuser if it's not
            if not existing_user.is_superuser or existing_user.role != UserRole.SUPER_ADMIN:
                existing_user.is_superuser = True
                existing_user.role = UserRole.SUPER_ADMIN
                existing_user.hashed_password = get_password_hash(password)
                session.add(existing_user)
                session.commit()
                print(f"Updated existing user {email} to super admin.")
            return

        # Create new superuser
        new_user = User(
            email=email,
            full_name="Super Admin",
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
            role=UserRole.SUPER_ADMIN
        )
        session.add(new_user)
        session.commit()
        print(f"Superuser {email} created successfully with role SUPER_ADMIN.")

if __name__ == "__main__":
    email = "nathnaelnigussie19@gmail.com"
    password = "Godisgood"
    create_superuser(email, password)
