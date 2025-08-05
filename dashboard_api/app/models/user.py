# backend/dashboard_api/app/models/user.py

from sqlalchemy import Column, String, DateTime, Text, Enum, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from db.base import Base


class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "auth_users"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    passwordHash = Column(
        "password_hash",
        String(255),
        nullable=False
    )

    userName = Column(
        "user_name",
        String(100),
        nullable=True
    )

    role = Column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False
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

    applications = relationship("Application", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
