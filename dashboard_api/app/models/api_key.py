# backend/dashboard_api/app/models/api_key.py

from sqlalchemy import Column, String, TIMESTAMP, Text, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
import uuid

from db.base import Base


class AppApiKey(Base):
    __tablename__ = "app_api_keys"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId = Column("user_id", CHAR(36), ForeignKey(
        "auth_users.id"), nullable=False)
    applicationId = Column("application_id", CHAR(36), ForeignKey(
        "user_applications.id"), unique=True, nullable=False)
    key = Column("key", String(255), unique=True, nullable=False)
    # 키 활성: 기본값=True
    isActive = Column("is_active", Boolean, default=True, nullable=False)
    createdAt = Column("created_at", TIMESTAMP,
                       server_default=func.now(), nullable=False)
    # 유효 기간: 0=무제한, 1=1일, 7=7일, 30=30일
    expiresAt = Column("expires_at", Integer, default=0, nullable=True)

    def __repr__(self):
        return f"<AppApiKey(id={self.id}, applicationId='{self.applicationId}', isActive={self.isActive})>"
