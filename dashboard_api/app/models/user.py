# backend/dashboard_api/app/models/user.py

from sqlalchemy import CHAR, Column, String, func
from sqlalchemy.types import DateTime
import uuid

from database import Base


class User(Base):  # BaseModelMixin을 먼저 상속받아 공통 필드를 포함시킵니다.
    __tablename__ = "auth_users"  # 테이블 이름을 명시적으로 지정합니다.

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, index=True, nullable=False)
    passwordHash = Column(String(255), nullable=False)
    userName = Column(String(100), nullable=False)
    createdAt = Column(DateTime(timezone=True),
                       server_default=func.now(), nullable=False)
    deletedAt = Column(DateTime(timezone=True), nullable=True)
