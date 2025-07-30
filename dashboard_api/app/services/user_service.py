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

    def get_user_by_id(self, userId: str) -> User:
        return self.userRepo.get_user_by_id(userId)

    def create_user(self, userData: UserCreate) -> User:
        """
        새로운 사용자를 데이터베이스에 추가합니다.
        """
        # 모든 상태의 사용자 (활성 또는 소프트 삭제됨) 중에서 이메일 중복을 확인합니다.
        existingUser = self.userRepo.get_user_by_email(
            userData.email, includeDeleted=True)

        if existingUser:
            # 이메일이 이미 존재하면 (소프트 삭제 상태 포함) None 반환하여 중복 알림
            return None

        hashedPassword = self.get_password_hash(userData.password)
        newUser = self.userRepo.create_user(userData, hashedPassword)

        return newUser

    def update_user(self, userId: str, userUpdate: UserUpdate) -> User:
        """
        사용자의 프로필 정보를 업데이트합니다.
        """

        dbUser = self.userRepo.get_user_by_id(userId)

        if not dbUser:
            return None  # 사용자를 찾을 수 없음

        updatedUser = self.userRepo.update_user(dbUser, userUpdate)

        return updatedUser

    def delete_user(self, userId: str) -> User:
        """
        User 객체를 소프트 삭제합니다.
        """
        dbUser = self.get_user_by_id(userId)

        if not dbUser:
            return None  # 사용자를 찾을 수 없음 (이미 소프트 삭제됨)

        deletedUser = self.userRepo.delete_user(dbUser)

        return deletedUser
