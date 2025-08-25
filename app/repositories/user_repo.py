# app/repositories/user_repo.py

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status

from app.models.user import User, UserSubscription
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: Session):
        """
        UserRepository의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db

    def getUserByEmail(self, email: str, includeDeleted: bool = False) -> Optional[User]:
        """
        이메일 주소를 사용하여 사용자를 조회합니다.

        Args:
            email (str): 조회할 사용자의 이메일 주소.
            includeDeleted (bool, optional): 소프트 삭제된 사용자를 포함할지 여부. Defaults to False.

        Returns:
            Optional[User]: 조회된 User 객체. 없으면 None을 반환합니다.
        """
        try:
            # 1. 이메일 주소를 기준으로 사용자 조회를 위한 기본 쿼리를 생성합니다.
            query = self.db.query(User).filter(User.email == email)

            # 2. `includeDeleted`가 False이면, 아직 삭제되지 않은(deletedAt is None) 사용자만 필터링합니다.
            if not includeDeleted:
                query = query.filter(User.deletedAt.is_(None))

            # 3. 쿼리를 실행하고 첫 번째 결과를 반환합니다.
            return query.first()
        except Exception as e:
            # 4. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"이메일로 사용자 조회 중 오류가 발생했습니다: {e}"
            )

    def getUserById(self, userId: int) -> Optional[User]:
        """
        사용자 ID를 사용하여 활성 사용자를 조회합니다.

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            Optional[User]: 조회된 User 객체. 없으면 None을 반환합니다.
        """
        try:
            # 1. 사용자 ID와 삭제되지 않음 조건을 만족하는 사용자를 조회하여 반환합니다.
            return self.db.query(User).filter(User.id == userId, User.deletedAt.is_(None)).first()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ID로 사용자 조회 중 오류가 발생했습니다: {e}"
            )

    def createUser(self, userData: UserCreate, hashedPassword: str) -> User:
        """
        새로운 사용자를 생성하고 데이터베이스에 저장합니다.

        Args:
            userData (UserCreate): 생성할 사용자의 데이터 (스키마).
            hashedPassword (str): 해시된 사용자 비밀번호.

        Returns:
            User: 새로 생성된 User 객체.
        """
        # 1. Pydantic 스키마와 해시된 비밀번호로 새로운 User 모델 객체를 생성합니다.
        user = User(
            email=userData.email,
            passwordHash=hashedPassword,
            userName=userData.userName,
        )
        try:
            # 2. 생성된 객체를 데이터베이스 세션에 추가합니다.
            self.db.add(user)
            # 3. 변경 사항을 데이터베이스에 커밋합니다.
            self.db.commit()
            # 4. 데이터베이스로부터 최신 상태(예: 자동 생성된 ID)를 객체에 반영합니다.
            self.db.refresh(user)
        except Exception as e:
            # 5. 오류 발생 시, 변경사항을 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용자 생성 중 오류가 발생했습니다: {e}"
            )
        # 6. 최종적으로 생성된 User 객체를 반환합니다.
        return user

    def updateUser(self, user: User, userUpdate: UserUpdate) -> User:
        """
        기존 사용자 객체의 정보를 업데이트합니다. (현재는 이름만 업데이트)

        Args:
            user (User): 정보을 수정할 기존 User 객체.
            userUpdate (UserUpdate): 적용할 새로운 데이터 (스키마).

        Returns:
            User: 정보가 수정된 User 객체.
        """
        # 1. userUpdate 스키마에 업데이트할 정보가 있는지 확인하고, 있으면 기존 객체의 속성을 변경합니다.
        if userUpdate.userName is not None:
            user.userName = userUpdate.userName

        # 참고: 비밀번호 변경 등 다른 필드 업데이트 로직도 여기에 추가될 수 있습니다.

        try:
            # 2. 변경된 사항을 데이터베이스에 커밋합니다.
            # user 객체는 이미 세션에 의해 추적되고 있으므로, 다시 add 할 필요가 없습니다.
            self.db.commit()
            # 3. 데이터베이스로부터 최신 상태를 객체에 반영합니다.
            self.db.refresh(user)
        except Exception as e:
            # 4. 오류 발생 시, 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용자 정보 업데이트 중 오류가 발생했습니다: {e}"
            )
        # 5. 수정된 User 객체를 반환합니다.
        return user

    def updateUserPlan(self, user: User, new_plan: UserSubscription) -> User:
        """
        사용자의 구독 플랜을 업데이트합니다.

        Args:
            user (User): 플랜을 수정할 기존 User 객체.
            new_plan (UserSubscription): 새로운 구독 플랜 Enum 값.

        Returns:
            User: 플랜이 수정된 User 객체.
        """
        # 1. 사용자의 plan 속성을 새로운 플랜으로 변경합니다.
        user.plan = new_plan
        try:
            # 2. 변경된 사항을 데이터베이스에 커밋합니다.
            self.db.commit()
            # 3. 데이터베이스로부터 최신 상태를 객체에 반영합니다.
            self.db.refresh(user)
        except Exception as e:
            # 4. 오류 발생 시, 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용자 구독 플랜 업데이트 중 오류가 발생했습니다: {e}"
            )
        # 5. 수정된 User 객체를 반환합니다.
        return user

    def deleteUser(self, user: User) -> User:
        """
        사용자 객체를 비활성화(소프트 삭제)합니다.

        Args:
            user (User): 비활성화할 User 객체.

        Returns:
            User: 비활성화된 User 객체.
        """
        # 1. 사용자의 삭제 시각(deletedAt)을 현재 시간으로 설정하여 소프트 삭제 처리합니다.
        user.deletedAt = datetime.now()
        try:
            # 2. 변경사항을 데이터베이스에 커밋합니다.
            self.db.commit()
            # 3. 데이터베이스로부터 최신 상태를 객체에 반영합니다.
            self.db.refresh(user)
        except Exception as e:
            # 4. 오류 발생 시, 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용자 삭제 중 오류가 발생했습니다: {e}"
            )
        # 5. 수정된 User 객체를 반환합니다.
        return user

    # def getAllUsersAdmin(self, includeDeleted: bool = False) -> List[User]:
    #     """
    #     [관리자용] 모든 사용자 목록을 조회합니다.

    #     Args:
    #         includeDeleted (bool, optional): 소프트 삭제된 사용자를 포함할지 여부. Defaults to False.

    #     Returns:
    #         List[User]: 조회된 User 객체의 리스트.
    #     """
    #     try:
    #         # 1. 모든 사용자를 조회하는 기본 쿼리를 생성합니다.
    #         query = self.db.query(User)
    #         # 2. `includeDeleted`가 False이면, 삭제되지 않은 사용자만 필터링합니다.
    #         if not includeDeleted:
    #             query = query.filter(User.deletedAt.is_(None))
    #         # 3. 쿼리를 실행하고 모든 결과를 리스트로 반환합니다.
    #         return query.all()
    #     except Exception as e:
    #         # 4. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"모든 사용자 조회 중 오류가 발생했습니다: {e}"
    #         )

    # def getUserByIdAdmin(self, userId: int, includeDeleted: bool = False) -> Optional[User]:
    #     """
    #     [관리자용] 사용자 ID로 사용자를 조회하며, 삭제된 사용자도 포함할 수 있습니다.

    #     Args:
    #         userId (int): 조회할 사용자의 ID.
    #         includeDeleted (bool, optional): 소프트 삭제된 사용자를 포함할지 여부. Defaults to False.

    #     Returns:
    #         Optional[User]: 조회된 User 객체. 없으면 None을 반환합니다.
    #     """
    #     try:
    #         # 1. 사용자 ID를 기준으로 조회를 위한 기본 쿼리를 생성합니다.
    #         query = self.db.query(User).filter(User.id == userId)
    #         # 2. `includeDeleted`가 False이면, 삭제되지 않은 사용자만 필터링합니다.
    #         if not includeDeleted:
    #             query = query.filter(User.deletedAt.is_(None))
    #         # 3. 쿼리를 실행하고 첫 번째 결과를 반환합니다.
    #         return query.first()
    #     except Exception as e:
    #         # 4. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"ID로 관리자용 사용자 조회 중 오류가 발생했습니다: {e}"
    #         )
