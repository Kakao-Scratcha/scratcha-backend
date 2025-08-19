# app/repositories/user_repo.py

from typing import List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str, includeDeleted: bool = False) -> User:
        query = self.db.query(User).filter(User.email == email)

        # includeDeleted가 False 일때 즉, 이메일이 삭제되지 않았을 때만 필터링
        if not includeDeleted:
            query = query.filter(User.deletedAt.is_(None))

        return query.first()

    def get_user_by_id(self, userId: str) -> User:
        return self.db.query(User).filter(User.id == userId, User.deletedAt.is_(None)).first()

    # 사용자 생성 CRUD
    def create_user(self, userData: UserCreate, hashedPassword: str) -> User:
        """
        새로운 사용자를 데이터베이스에 추가합니다.
        """
        dbUser = User(
            email=userData.email,
            passwordHash=hashedPassword,
            userName=userData.userName,
        )
        self.db.add(dbUser)
        self.db.commit()
        self.db.refresh(dbUser)
        return dbUser

    # 사용자 정보 업데이트 CURD

    def update_user(self, dbUser: User, userUpdate: UserUpdate) -> User:
        """
        User 객체의 정보를 UserUpdate 스키마에 따라 업데이트합니다.
        """

        self.db.add(dbUser)  # 변경 감지 및 스테이징
        self.db.commit()     # DB에 변경 사항 반영
        self.db.refresh(dbUser)  # 최신 데이터로 객체 새로고침
        return dbUser

    def update_user_plan(self, dbUser: User, new_plan: str) -> User:
        """
        사용자의 구독 플랜을 업데이트합니다.
        """
        dbUser.plan = new_plan
        self.db.add(dbUser)
        self.db.commit()
        self.db.refresh(dbUser)
        return dbUser

    # 사용자 삭제 (soft delete) CRUD

    def delete_user(self, dbUser: User) -> User:
        """
        User 객체를 소프트 삭제합니다.
        """
        dbUser.deletedAt = datetime.now()
        self.db.add(dbUser)
        self.db.commit()
        self.db.refresh(dbUser)
        return dbUser

    # 모든 사용자 조회 (관리자용)
    def get_all_users_admin(self, includeDeleted: bool = False) -> List[User]:
        """
        관리자용: 모든 사용자를 조회합니다. includeDeleted가 True이면 소프트 삭제된 사용자도 포함합니다.
        """
        query = self.db.query(User)
        if not includeDeleted:
            query = query.filter(User.deletedAt.is_(None))
        return query.all()

    # 특정 ID의 사용자 조회 (삭제된 사용자 포함 가능, 관리자용)
    def get_user_by_id_admin(self, userId: str, includeDeleted: bool = False) -> User | None:
        """
        관리자용: 특정 ID의 사용자를 조회합니다. includeDeleted에 따라 삭제된 사용자도 포함할 수 있습니다.
        """
        query = self.db.query(User).filter(User.id == userId)
        if not includeDeleted:
            query = query.filter(User.deletedAt.is_(None))
        return query.first()
