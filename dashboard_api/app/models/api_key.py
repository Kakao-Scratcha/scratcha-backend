# backend/dashboard_api/app/models/api_key.py

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.base import Base


class AppApiKey(Base):
    __tablename__ = "app_api_keys"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    userId = Column(
        "user_id",
        Integer,
        ForeignKey("auth_users.id"),
        nullable=False
    )

    appId = Column(
        "application_id",
        Integer,
        ForeignKey("user_applications.id"),
        nullable=False
    )

    key = Column(
        "key",
        String(255),
        unique=True,
        nullable=False
    )
    # 키 활성: 기본값=True
    isActive = Column(
        "is_active",
        Boolean,
        default=True,
        nullable=False
    )

    expiresAt = Column(
        "expires_at",
        DateTime,
        nullable=True
    )

    createdAt = Column(
        "created_at",
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    updatedAt = Column(
        "updated_at",
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    deletedAt = Column(
        "deleted_at",
        DateTime,
        nullable=True
    )

    application = relationship("Application", back_populates="api_keys")

    def __repr__(self):
        return f"<AppApiKey(id={self.id}, appId='{self.appId}', isActive={self.isActive})>"
