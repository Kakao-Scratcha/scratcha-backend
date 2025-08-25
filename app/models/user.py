# backend/models/user.py

from sqlalchemy import Column, String, DateTime, Enum, Integer, func
from sqlalchemy.orm import relationship
import enum

from db.base import Base


class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class UserSubscription(enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(Base):
    __tablename__ = "user"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="유저 ID"
    )
    email = Column(
        "email",
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="로그인 이메일"
    )

    passwordHash = Column(
        "password_hash",
        String(255),
        nullable=False,
        comment="비밀번호 해시"
    )

    userName = Column(
        "user_name",
        String(100),
        nullable=True,
        comment="사용자 이름"
    )

    role = Column(
        "role",
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
        comment="사용자 권한"
    )

    plan = Column(
        "subscription_plan",
        Enum(UserSubscription),
        default=UserSubscription.FREE,
        nullable=False,
        comment="구독한 플랜"
    )

    token = Column(
        "api_token",
        Integer,
        default=1000,
        nullable=False,
        comment="API 호출 토큰 개수"
    )

    createdAt = Column(
        "created_at",
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="생성 시각"
    )

    updatedAt = Column(
        "updated_at",
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="수정 시각"
    )

    deletedAt = Column(
        "deleted_at",
        DateTime,
        nullable=True,
        comment="삭제 시각 (soft-delete)"
    )

    # 1:N 관계
    application = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",  # 부모가 삭제될 때 자식도 함꼐 삭제
    )
