# backend/dashboard_api/app/services/user_service.py
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from models.user import User
from repositories.user_repo import UserRepository
from schemas.user import UserCreate, UserUpdate

pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:

    def __init__(self, db: Session):
        self.userRepo = UserRepository(db)

    def get_password_hash(self, password: str) -> str:
        return pwdContext.hash(password)

    def create_user(self, userData: UserCreate) -> User | None:
        existingUser = self.userRepo.get_user_by_email(userData.email)

        if existingUser:
            return None  # 이메일 중복일 시 None 반환

        hashedPassword = self.get_password_hash(userData.password)
        newUser = self.userRepo.create_user(userData, hashedPassword)

        return newUser

    def get_user_by_id(self, userId: str) -> User | None:
        return self.userRepo.get_user_by_id(userId)

    # 사용자 정보 업데이트
    def update_user(self, userId: str, userUpdate: UserUpdate) -> User | None:
        """
        특정 사용자의 프로필 정보를 업데이트합니다.
        """

        db_user = self.userRepo.get_user_by_id(userId)

        if not db_user:
            return None  # 사용자를 찾을 수 없음

        updated_user = self.userRepo.update_user(db_user, userUpdate)

        return updated_user
