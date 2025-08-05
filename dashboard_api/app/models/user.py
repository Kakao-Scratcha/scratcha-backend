# backend/dashboard_api/app/models/user.py

from sqlalchemy import Column, String, TIMESTAMP, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
import uuid
import enum

from db.base import Base


class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "auth_users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    passwordHash = Column("password_hash", String(255), nullable=False)
    userName = Column("user_name", String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    createdAt = Column("created_at", TIMESTAMP,
                       server_default=func.now(), nullable=False)
    deletedAt = Column("deleted_at", TIMESTAMP, nullable=True)

    applications = relationship("Application", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
