# backend/services/user_service.py

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import re

from app.core.security import getPasswordHash, verifyPassword
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserPlanUpdate
from app.models.user import User, UserRole


USER_NAME_PATTERN = re.compile(r"^[가-힣a-zA-Z0-9]+$")


class UserService:

    def __init__(self, db: Session):
        self.userRepo = UserRepository(db)

    def getUserById(self, userId: str) -> User:
        return self.userRepo.getUserById(userId)

    def createUser(self, userData: UserCreate) -> User:
        """
        새로운 사용자를 데이터베이스에 추가합니다.
        """
        # 모든 상태의 사용자 (활성 또는 소프트 삭제됨) 중에서 이메일 중복을 확인합니다.
        existingUser = self.userRepo.getUserByEmail(
            userData.email, includeDeleted=True)

        if existingUser:
            # 이메일이 이미 존재하면 (소프트 삭제 상태 포함) None 반환하여 중복 알림
            return None

        hashedPassword = getPasswordHash(userData.password)
        newUser = self.userRepo.createUser(userData, hashedPassword)

        return newUser

    def updateUser(self, userId: str, userUpdate: UserUpdate) -> User:
        """사용자의 프로필 정보를 업데이트합니다."""

        user = self.getUserById(userId)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        # 1. 사용자 이름 유효성 검증
        if userUpdate.userName is not None:
            if not USER_NAME_PATTERN.match(userUpdate.userName):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="사용자 이름에는 한글, 영문, 숫자만 사용할 수 있습니다."
                )

            # 사용자 이름 유효성 검사 확인
            if userUpdate.userName:
                if userUpdate.userName.isdigit():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="사용자 이름은 숫자로만 구성될 수 없습니다."
                    )
            user.userName = userUpdate.userName

        # 2. 비밀번호 변경 로직
        if userUpdate.newPassword:

            # 새 비밀번호 필드가 둘 중 하나라도 존재하면 비밀번호 변경으로 간주
            if not userUpdate.currnetPassword or not userUpdate.newPassword or not userUpdate.confirmPassword:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="비밀번호를 변경하려면 현재 비밀번호, 새 비밀번호, 새 비밀번호 확인 모두 입력해야 합니다."
                )

            # 새 비밀번호와 확인 비밀번호가 일치하는지 검증
            if userUpdate.newPassword != userUpdate.confirmPassword:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="새 비밀번호와 확인 비밀번호가 일치하지 않습니다."
                )

            # 현재 비밀번호가 일치하는지 검증
            if not verifyPassword(userUpdate.currnetPassword, user.passwordHash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="현재 비밀번호가 일치하지 않습니다."
                )

            # 새 비밀번호가 현재 비밀번호와 동일한지 검증
            if userUpdate.newPassword == userUpdate.currnetPassword:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="새 비밀번호는 현재 비밀번호와 동일할 수 없습니다."
                )
            # 새 비밀번호를 해싱하여 user 객체에 할당
            user.passwordHash = getPasswordHash(userUpdate.newPassword)

        updatedUser = self.userRepo.updateUser(user, userUpdate)

        return updatedUser

    def updateUserPlan(self, userId: int, planUpdate: UserPlanUpdate, currentUser: User) -> User:
        """
        사용자의 구독 플랜을 업데이트합니다.
        """
        user = self.userRepo.getUserById(userId)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        # 권한 확인: 현재 사용자가 업데이트 대상 사용자이거나 관리자여야 합니다.
        if currentUser.id != userId and currentUser.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="플랜을 업데이트할 권한이 없습니다."
            )

        updated_user = self.userRepo.updateUserPlan(user, planUpdate.plan)
        return updated_user

    def deleteUser(self, userId: str) -> User:
        """
        User 객체를 소프트 삭제합니다.
        """
        user = self.getUserById(userId)

        if not user:
            return None  # 사용자를 찾을 수 없음 (이미 소프트 삭제됨)

        deletedUser = self.userRepo.deleteUser(user)

        return deletedUser

    # (관리자용) 모든 사용자 목록 조회
    def getAllUsersAdmin(self, includeDeleted: bool = False) -> List[User]:
        """
        관리자용: 모든 사용자 목록을 조회합니다.
        """
        return self.userRepo.getAllUsersAdmin(includeDeleted)

    # (관리자용) 특정 사용자 조회
    def getUserAdmin(self, userId: str, includeDeleted: bool = False) -> User | None:
        """
        관리자용: 특정 사용자를 조회합니다.
        """
        return self.userRepo.getUserByIdAdmin(userId, includeDeleted)

    # (관리자용) 사용자 계정 복구
    def restoreUserAdmin(self, userId: str) -> User | None:
        """
        관리자용: 특정 사용자의 계정을 복구합니다.
        """
        # 소프트 삭제된 사용자도 포함하여 조회합니다.
        user = self.userRepo.getUserByIdAdmin(
            userId, includeDeleted=True)
        if not user or user.deletedAt is None:
            # 사용자를 찾을 수 없거나 이미 삭제되지 않은 경우
            return None

        user.deletedAt = None  # deletedAt을 NULL로 설정하여 복구
        self.userRepo.db.add(user)
        self.userRepo.db.commit()
        self.userRepo.db.refresh(user)
        return user
