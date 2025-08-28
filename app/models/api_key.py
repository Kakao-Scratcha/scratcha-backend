# backend/models/api_key.py

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.core.config import settings

from db.base import Base


class ApiKey(Base):
    __tablename__ = "api_key"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="키 ID"
    )

    userId = Column(
        "user_id",
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="키 소유자"
    )

    appId = Column(
        "application_id",
        Integer,
        ForeignKey("application.id", ondelete="CASCADE"),
        nullable=False,
        comment="애플리케이션과 1:1"
    )

    key = Column(
        "key",
        String(255),
        unique=True,
        nullable=False,
        comment="외부 노출용 API 키 문자열"
    )
    # 키 활성: 기본값=True
    isActive = Column(
        "is_active",
        Boolean,
        default=True,
        nullable=False,
        comment="키 활성 상태"
    )

    expiresAt = Column(
        "expires_at",
        DateTime(timezone=True),
        nullable=True,
        comment="만료 시각 : 0 >= 무제한, 1=1일, 7=7일, 30=30일 등"
    )

    createdAt = Column(
        "created_at",
        DateTime(timezone=True),
        default=lambda: datetime.now(settings.TIMEZONE),
        nullable=False,
        comment="생성 시각"
    )

    updatedAt = Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="수정 시각"
    )

    deletedAt = Column(
        "deleted_at",
        DateTime(timezone=True),
        nullable=True,
        comment="삭제 시각 (soft-delete)"
    )

    # N:1 관계
    user = relationship("User")
    application = relationship("Application", back_populates="apiKey")

    captchaLog = relationship("CaptchaLog", back_populates="apiKey")
    usageStats = relationship("UsageStats", back_populates="apiKey")
