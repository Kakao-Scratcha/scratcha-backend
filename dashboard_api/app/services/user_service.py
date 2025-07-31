# backend/dashboard_api/app/services/user_service.py

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional, List
from datetime import datetime

from dashboard_api.app.models.user import User
from dashboard_api.app.repositories.user_repo import UserRepository
from dashboard_api.app.schemas.user import UserCreate, UserUpdate


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

    # (관리자용) 모든 사용자 목록 조회
    def get_all_users_admin(self, includeDeleted: bool = False) -> List[User]:
        """
        관리자용: 모든 사용자 목록을 조회합니다.
        """
        return self.userRepo.get_all_users_admin(includeDeleted)

    # (관리자용) 특정 사용자 조회
    def get_user_admin(self, userId: str, includeDeleted: bool = False) -> User | None:
        """
        관리자용: 특정 사용자를 조회합니다.
        """
        return self.userRepo.get_user_by_id_admin(userId, includeDeleted)

    # (관리자용) 사용자 계정 복구
    def restore_user_admin(self, userId: str) -> User | None:
        """
        관리자용: 특정 사용자의 계정을 복구합니다.
        """
        # 소프트 삭제된 사용자도 포함하여 조회합니다.
        dbUser = self.userRepo.get_user_by_id_admin(
            userId, includeDeleted=True)
        if not dbUser or dbUser.deletedAt is None:
            # 사용자를 찾을 수 없거나 이미 삭제되지 않은 경우
            return None

        dbUser.deletedAt = None  # deletedAt을 NULL로 설정하여 복구
        self.userRepo.db.add(dbUser)
        self.userRepo.db.commit()
        self.userRepo.db.refresh(dbUser)
        return dbUser
