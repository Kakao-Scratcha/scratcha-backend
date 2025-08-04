# dashboard_api/app/repositories/api_key_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import uuid
import secrets

from dashboard_api.app.models.api_key import AppApiKey
from typing import Optional


class AppApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def generate_api_key(self) -> str:
        """API 키를 생성합니다."""

        return f"{secrets.token_hex(32)}"  # secrets 모듈 사용 권장

    def create_api_key(self, userId: str, applicationId: str, expiration_policy_days: int = 0) -> AppApiKey:
        """특정 애플리케이션에 대한 API 키를 생성합니다. commit은 서비스 계층에서 수행합니다."""

        key = self.generate_api_key()

        # 만료 정책(일)에 따라 만료 시점(expiresAt)을 계산합니다.
        expiresAt = None  # 기본값은 무제한(None)
        if expiration_policy_days > 0:
            # 정책 값이 양수이면, 현재 시간에서 해당 일수만큼 더해 만료 시점을 설정합니다.
            expiresAt = datetime.now() + timedelta(days=expiration_policy_days)

        dbApiKey = AppApiKey(
            id=str(uuid.uuid4()),
            userId=userId,
            applicationId=applicationId,
            key=key,
            isActive=True,
            expiresAt=expiresAt
        )

        self.db.add(dbApiKey)
        return dbApiKey

    def get_api_key_by_app_id(self, applicationId: str) -> Optional[AppApiKey]:
        """applicationId를 기준으로 API 키를 조회합니다."""
        return self.db.query(AppApiKey).filter(AppApiKey.applicationId == applicationId).first()

    def deactivate_api_key(self, apiKey: AppApiKey) -> AppApiKey:
        """API 키를 비활성화합니다. commit은 서비스 계층에서 수행합니다."""
        apiKey.isActive = False
        self.db.add(apiKey)
        return apiKey
