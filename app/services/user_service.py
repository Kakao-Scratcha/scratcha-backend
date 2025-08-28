# services/user_service.py

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import re

from app.core.security import getPasswordHash, verifyPassword
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserPlanUpdate
from app.models.user import User, UserRole
from app.core.config import settings # settings 객체 임포트


class UserService:
    """
    사용자 관련 비즈니스 로직을 처리하는 서비스 클래스입니다.
    """

    def __init__(self, db: Session):
        """
        UserService의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.userRepo = UserRepository(db)

    def getUserById(self, userId: str) -> User:
        """
        사용자 ID로 사용자를 조회합니다.

        Args:
            userId (str): 조회할 사용자의 ID.

        Returns:
            User: 조회된 사용자 객체. 없을 경우 None을 반환합니다.
        """
        # 1. UserRepository를 통해 사용자 ID로 사용자를 조회합니다.
        return self.userRepo.getUserById(userId)

    def createUser(self, userData: UserCreate) -> User:
        """
        새로운 사용자를 생성합니다.

        Args:
            userData (UserCreate): 생성할 사용자의 데이터 (스키마).

        Returns:
            User: 새로 생성된 사용자 객체. 이메일이 이미 존재하면 None을 반환합니다.
        """
        # 1. 삭제된 사용자를 포함하여 모든 사용자 중에서 이메일 중복을 확인합니다.
        existingUser = self.userRepo.getUserByEmail(
            userData.email, includeDeleted=True)

        # 2. 이메일이 이미 존재하는 경우 None을 반환하여 중복을 알립니다.
        if existingUser:
            return None

        # 3. 비밀번호를 해시 처리합니다.
        hashedPassword = getPasswordHash(userData.password)
        # 4. UserRepository를 통해 새로운 사용자를 생성합니다.
        newUser = self.userRepo.createUser(userData, hashedPassword)

        # 5. 생성된 사용자 객체를 반환합니다.
        return newUser

    def updateUser(self, userId: str, userUpdate: UserUpdate) -> User:
        """
        사용자의 프로필 정보를 업데이트합니다.

        Args:
            userId (str): 업데이트할 사용자의 ID.
            userUpdate (UserUpdate): 업데이트할 사용자의 데이터 (스키마).

        Returns:
            User: 업데이트된 사용자 객체.

        Raises:
            HTTPException: 사용자를 찾을 수 없거나, 입력 데이터가 유효하지 않을 경우 발생합니다.
        """
        # 1. 업데이트할 사용자를 조회합니다.
        user = self.getUserById(userId)

        # 2. 사용자가 존재하지 않으면 404 오류를 발생시킵니다.
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        # 3. 사용자 이름 유효성 검증 및 업데이트
        if userUpdate.userName is not None:
            if not re.match(settings.USER_NAME_REGEX_PATTERN, userUpdate.userName): # 정규식 패턴 사용
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="사용자 이름에는 한글, 영문, 숫자, 특수문자(.-_) 만 사용할 수 있습니다."
                )
            if userUpdate.userName.isdigit():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="사용자 이름은 숫자로만 구성될 수 없습니다."
                )
            user.userName = userUpdate.userName

        # 4. 비밀번호 변경 로직
        if userUpdate.newPassword:
            if not userUpdate.currnetPassword or not userUpdate.newPassword or not userUpdate.confirmPassword:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="비밀번호를 변경하려면 현재 비밀번호, 새 비밀번호, 새 비밀번호 확인 모두 입력해야 합니다."
                )
            if userUpdate.newPassword != userUpdate.confirmPassword:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="새 비밀번호와 확인 비밀번호가 일치하지 않습니다."
                )
            if not verifyPassword(userUpdate.currnetPassword, user.passwordHash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="현재 비밀번호가 일치하지 않습니다."
                )
            if userUpdate.newPassword == userUpdate.currnetPassword:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="새 비밀번호는 현재 비밀번호와 동일할 수 없습니다."
                )
            user.passwordHash = getPasswordHash(userUpdate.newPassword)

        # 5. UserRepository를 통해 사용자 정보를 업데이트합니다.
        updatedUser = self.userRepo.updateUser(user, userUpdate)

        # 6. 업데이트된 사용자 객체를 반환합니다.
        return updatedUser

    def updateUserPlan(self, userId: int, planUpdate: UserPlanUpdate, currentUser: User) -> User:
        """
        사용자의 구독 플랜을 업데이트합니다. 관리자 또는 본인만 가능합니다.

        Args:
            userId (int): 플랜을 업데이트할 사용자의 ID.
            planUpdate (UserPlanUpdate): 새로운 플랜 정보.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            User: 플랜이 업데이트된 사용자 객체.

        Raises:
            HTTPException: 사용자를 찾을 수 없거나, 권한이 없는 경우 발생합니다.
        """
        # 1. 플랜을 업데이트할 사용자를 조회합니다.
        user = self.userRepo.getUserById(userId)

        # 2. 사용자가 존재하지 않으면 404 오류를 발생시킵니다.
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        # 3. 권한 확인: 현재 사용자가 대상 사용자 본인이거나 관리자인지 확인합니다.
        if currentUser.id != userId and currentUser.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="플랜을 업데이트할 권한이 없습니다."
            )

        # 4. UserRepository를 통해 사용자의 플랜을 업데이트합니다.
        updated_user = self.userRepo.updateUserPlan(user, planUpdate.plan)
        # 5. 업데이트된 사용자 객체를 반환합니다.
        return updated_user

    def deleteUser(self, userId: str) -> User:
        """
        사용자를 소프트 삭제합니다.

        Args:
            userId (str): 삭제할 사용자의 ID.

        Returns:
            User: 소프트 삭제된 사용자 객체. 사용자를 찾을 수 없으면 None을 반환합니다.
        """
        # 1. 삭제할 사용자를 조회합니다.
        user = self.getUserById(userId)

        # 2. 사용자가 존재하지 않으면 None을 반환합니다.
        if not user:
            return None

        # 3. UserRepository를 통해 사용자를 소프트 삭제합니다.
        deletedUser = self.userRepo.deleteUser(user)

        # 4. 삭제된 사용자 객체를 반환합니다.
        return deletedUser

    def getAllUsersAdmin(self, includeDeleted: bool = False) -> List[User]:
        """
        (관리자용) 모든 사용자 목록을 조회합니다.

        Args:
            includeDeleted (bool, optional): 삭제된 사용자를 포함할지 여부. Defaults to False.

        Returns:
            List[User]: 모든 사용자 객체의 리스트.
        """
        # 1. UserRepository를 통해 모든 사용자 목록을 조회합니다.
        return self.userRepo.getAllUsersAdmin(includeDeleted)

    def getUserAdmin(self, userId: str, includeDeleted: bool = False) -> User | None:
        """
        (관리자용) 특정 사용자를 조회합니다.

        Args:
            userId (str): 조회할 사용자의 ID.
            includeDeleted (bool, optional): 삭제된 사용자를 포함할지 여부. Defaults to False.

        Returns:
            User | None: 조회된 사용자 객체. 없을 경우 None을 반환합니다.
        """
        # 1. UserRepository를 통해 특정 사용자를 조회합니다.
        return self.userRepo.getUserByIdAdmin(userId, includeDeleted)

    def restoreUserAdmin(self, userId: str) -> User | None:
        """
        (관리자용) 특정 사용자의 계정을 복구합니다.

        Args:
            userId (str): 복구할 사용자의 ID.

        Returns:
            User | None: 복구된 사용자 객체. 사용자를 찾을 수 없거나 이미 활성 상태이면 None을 반환합니다.
        """
        # 1. 삭제된 사용자를 포함하여 복구할 사용자를 조회합니다.
        user = self.userRepo.getUserByIdAdmin(
            userId, includeDeleted=True)
        # 2. 사용자가 없거나 이미 활성 상태인 경우 None을 반환합니다.
        if not user or user.deletedAt is None:
            return None

        # 3. deletedAt을 None으로 설정하여 사용자를 복구합니다.
        user.deletedAt = None
        self.userRepo.db.add(user)
        self.userRepo.db.commit()
        self.userRepo.db.refresh(user)
        # 4. 복구된 사용자 객체를 반환합니다.
        return user

    def updateUserAdmin(self, userId: str, userUpdate: UserUpdate) -> User | None:
        """
        (관리자용) 특정 사용자의 정보를 업데이트합니다.

        Args:
            userId (str): 업데이트할 사용자의 ID.
            userUpdate (UserUpdate): 업데이트할 사용자의 데이터 (스키마).

        Returns:
            User | None: 업데이트된 사용자 객체. 사용자를 찾을 수 없으면 None을 반환합니다.
        """
        # 1. 삭제된 사용자를 포함하여 업데이트할 사용자를 조회합니다.
        user = self.userRepo.getUserByIdAdmin(
            userId, includeDeleted=True)
        # 2. 사용자가 없으면 None을 반환합니다.
        if not user:
            return None

        # 3. 요청된 데이터를 기반으로 사용자 정보를 업데이트합니다.
        if userUpdate.userName is not None:
            user.userName = userUpdate.userName
        if userUpdate.newPassword:
            user.passwordHash = getPasswordHash(userUpdate.newPassword)
        if userUpdate.role is not None:
            user.role = userUpdate.role
        if userUpdate.plan is not None:
            user.plan = userUpdate.plan

        # 4. 변경사항을 데이터베이스에 커밋합니다.
        self.userRepo.db.commit()
        self.userRepo.db.refresh(user)
        # 5. 업데이트된 사용자 객체를 반환합니다.
        return user

    def deleteUserPermanentAdmin(self, userId: str) -> bool:
        """
        (관리자용) 특정 사용자의 계정을 영구적으로 삭제합니다.

        Args:
            userId (str): 영구 삭제할 사용자의 ID.

        Returns:
            bool: 삭제 성공 시 True, 사용자를 찾을 수 없으면 False를 반환합니다.
        """
        # 1. 삭제된 사용자를 포함하여 영구 삭제할 사용자를 조회합니다.
        user = self.userRepo.getUserByIdAdmin(
            userId, includeDeleted=True)
        # 2. 사용자가 없으면 False를 반환합니다.
        if not user:
            return False

        # 3. 데이터베이스에서 사용자를 영구적으로 삭제합니다.
        self.userRepo.db.delete(user)
        self.userRepo.db.commit()
        # 4. 삭제 성공 시 True를 반환합니다.
        return True