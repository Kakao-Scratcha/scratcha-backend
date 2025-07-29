# backend/dashboard_api/app/repositories/user_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.user import User
from schemas.user import UserCreate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, userId: str) -> User | None:
        return self.db.query(User).filter(User.id == userId).first()

    def create_user(self, userData: UserCreate, hashedPassword: str) -> User | None:

        db_user = User(
            email=userData.email,
            passwordHash=hashedPassword,
            userName=userData.userName,
        )

        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except IntegrityError:
            self.db.rollback()
            return None
