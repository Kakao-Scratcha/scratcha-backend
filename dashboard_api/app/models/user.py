# backend/dashboard_api/app/models/user.py

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from database import Base  # Base 임포트
import uuid


class User(Base):
    __tablename__ = "auth_users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, nullable=False)        # 로그인용 이메일
    passwordHash = Column("password_hash", String(
        255), nullable=False)                                       # 비밀번호 해시
    userName = Column("user_name", String(100), nullable=False)     # 사용자 이름
    role = Column(String(50), default="user", nullable=False)
    createdAt = Column("created_at", DateTime, server_default=func.now(
    ), nullable=False)
    # 탈퇴 시각 (soft delete)
    deletedAt = Column("deleted_at", DateTime, nullable=True)

    def __repr__(self):
        return f"<User(email='{self.email}', userName='{self.userName}', role='{self.role}')>"
