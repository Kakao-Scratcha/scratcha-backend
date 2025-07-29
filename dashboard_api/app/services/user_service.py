# backend/dashboard_api/app/services/user_service.py
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from models.user import User
from repositories.user_repo import UserRepository
from schemas.user import UserCreate

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
