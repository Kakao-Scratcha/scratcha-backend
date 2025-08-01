# backend/dashboard_api/app/models/application.py

from sqlalchemy import Column, String, TIMESTAMP, Text, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
import uuid

from db.base import Base


class UserApplication(Base):
    __tablename__ = "user_applications"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId = Column("user_id", CHAR(36), ForeignKey(
        "auth_users.id"), nullable=False)
    appName = Column("app_name", String(100), nullable=False)
    description = Column(Text, nullable=False)
    createdAt = Column("created_at", TIMESTAMP,
                       server_default=func.now(), nullable=False)
    deletedAt = Column("deleted_at", TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<UserApplication(id={self.id}, appName='{self.appName}', userId='{self.userId}')>"
