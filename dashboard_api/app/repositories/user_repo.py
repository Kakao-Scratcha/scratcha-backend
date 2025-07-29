# backend/dashboard_api/app/repositories/user_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.user import User
from schemas.user import UserCreate, UserUpdate


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

    # 사용자 정보 업데이트
    def update_user(self, db_user: User, user_update: UserUpdate) -> User:
        """
        주어진 User 객체의 정보를 UserUpdate 스키마에 따라 업데이트합니다.
        """
        update_data = user_update.model_dump(exclude_unset=True)  # Pydantic v2

        for key, value in update_data.items():
            setattr(db_user, key, value)

        self.db.add(db_user)  # 변경 감지 및 스테이징
        self.db.commit()     # DB에 변경 사항 반영
        self.db.refresh(db_user)  # 최신 데이터로 객체 새로고침
        return db_user
