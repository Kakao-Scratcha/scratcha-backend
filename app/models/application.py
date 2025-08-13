# backend/models/application.py

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.base import Base


class Application(Base):
    __tablename__ = "application"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="앱 ID"
    )

    userId = Column(
        "user_id",
        Integer,
        # User가 삭제될 때 이 레코드도 함께 삭제되도록 합니다.
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="사용자 FK"
    )

    appName = Column(
        "app_name",
        String(100),
        nullable=False,
        comment="앱 이름"
    )

    description = Column(
        "description",
        Text,
        nullable=True,
        comment="앱 설명"
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

    # N:1 관계
    user = relationship(
        "User",
        back_populates="application"
    )

    # 1:1 관계
    api_key = relationship(
        "ApiKey",
        back_populates="application",
        uselist=False,  # 단일 객체임을 명시
        cascade="all, delete-orphan"
    )
