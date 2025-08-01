# dashboard_api/app/repositories/api_key_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid
import secrets

from ..models.application import UserApplication
from ..models.api_key import AppApiKey
from ..schemas.application import ApplicationCreate, ApplicationUpdate
from typing import Optional


class AppApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def generate_api_key(self) -> str:
        """API 키를 생성합니다."""

        return f"sk_live_{secrets.token_hex(32)}"  # secrets 모듈 사용 권장

    def create_api_key(self, userId: str, applicationId: str) -> AppApiKey:
        """특정 애플리케이션에 대한 API 키를 생성합니다"""

        key = self.generate_api_key()

        dbApiKey = AppApiKey(
            id=str(uuid.uuid4()),
            userId=userId,
            applicationId=applicationId,
            key=key,
            isActive=True,
            createdAt=datetime.now(),
            expiresAt=0
        )

        self.db.add(dbApiKey)
        self.db.commit()
        self.db.refresh(dbApiKey)

        return dbApiKey
