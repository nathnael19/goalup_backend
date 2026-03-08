"""
Script to create an initial SUPER_ADMIN user directly in the Neon database.
Uses custom password hashing — no Supabase Auth dependency.

Usage:
    cd goalup_backend
    source venv/bin/activate
    python -m app.scripts.create_admin
"""
import sys
import os
import getpass
from dotenv import load_dotenv

# Add project root to path so imports work when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

from sqlmodel import Session, create_engine, select
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def create_admin_user(email: str, password: str, full_name: str):
    """Create a SUPER_ADMIN user directly in the Neon database."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL not set in .env")
        sys.exit(1)

    engine = create_engine(db_url, connect_args={"sslmode": "require"})

    with Session(engine) as session:
        # Check if user already exists
        existing = session.exec(select(User).where(User.email == email)).first()

        if existing:
            print(f"ℹ️  User '{email}' already exists.")
            if existing.role != UserRole.SUPER_ADMIN or not existing.is_superuser:
                print("   Upgrading to SUPER_ADMIN...")
                existing.role = UserRole.SUPER_ADMIN
                existing.is_superuser = True
                existing.hashed_password = get_password_hash(password)
                session.add(existing)
                session.commit()
                print("✅ User upgraded to SUPER_ADMIN successfully!")
            else:
                print("   User is already SUPER_ADMIN. Updating password...")
                existing.hashed_password = get_password_hash(password)
                session.add(existing)
                session.commit()
                print("✅ Password updated.")
            return

        # Create new admin user
        new_user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_superuser=True,
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        print(f"✅ Admin user created successfully!")
        print(f"   Email    : {email}")
        print(f"   Full Name: {full_name}")
        print(f"   ID       : {new_user.id}")


if __name__ == "__main__":
    print("\n--- Create GoalUp Admin User ---")
    email = input("Email: ").strip()
    full_name = input("Full Name: ").strip()
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        try:
            # Prefer hidden input in interactive terminals
            if sys.stdin.isatty():
                password = getpass.getpass("Password: ")
            else:
                # Non-interactive (e.g. CI / piped input): fall back to plain input
                password = input("Password: ")
        except Exception:
            password = None

    if not email or not full_name or not password:
        print("❌ Error: All fields are required.")
        sys.exit(1)

    create_admin_user(email, password, full_name)
