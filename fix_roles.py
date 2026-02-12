from sqlalchemy import create_engine, text
from app.core.config import settings
from sqlmodel import Session, select
from app.models.user import User, UserRole

engine = create_engine(settings.DATABASE_URL)

def fix_and_upgrade():
    with Session(engine) as session:
        # Fix existing lowercase roles
        session.execute(text("UPDATE users SET role = 'VIEWER' WHERE role = 'viewer'"))
        session.execute(text("UPDATE users SET role = 'SUPER_ADMIN' WHERE role = 'super_admin'"))
        session.commit()
        
        # Upgrade first user
        statement = select(User).limit(1)
        user = session.exec(statement).first()
        if user:
            print(f"Upgrading user {user.email} to SUPER_ADMIN...")
            user.role = UserRole.SUPER_ADMIN
            user.is_superuser = True
            session.add(user)
            session.commit()
            print("Upgrade successful.")
        else:
            print("No users found.")

if __name__ == "__main__":
    fix_and_upgrade()
