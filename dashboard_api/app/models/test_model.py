# dashboard_api/app/models/test_model.py

from sqlalchemy import Column, String, Integer, TIMESTAMP
from sqlalchemy.sql import func
import uuid

from db.base import Base


class TestModel(Base):
    __tablename__ = "test_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    value = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<TestModel(id={self.id}, name='{self.name}')>"
