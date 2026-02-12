from sqlmodel import Session, select, create_engine
from app.core.database import get_session
from app.models.user import User, UserRole
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

def upgrade_first_user():
    with Session(engine) as session:
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
            print("No users found in database.")

if __name__ == "__main__":
    upgrade_first_user()
