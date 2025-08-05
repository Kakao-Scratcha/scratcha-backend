# backend/dashboard_api/app/models/application.py

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from db.base import Base


class Application(Base):
    __tablename__ = "user_applications"

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

    appName = Column(
        "app_name",
        String(100),
        nullable=False
    )

    description = Column(
        Text,
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

    user = relationship("User", back_populates="applications")
    api_keys = relationship(
        "AppApiKey", back_populates="application", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application(id={self.id}, appName='{self.appName}', userId='{self.userId}')>"
