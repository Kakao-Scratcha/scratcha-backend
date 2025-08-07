# dashboard_api/app/repositories/api_key_repo.py

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import secrets

from dashboard_api.app.models.api_key import AppApiKey


class AppApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_key(self, userId: int, appId: int, expiresPolicy: int = 0) -> AppApiKey:
        """특정 애플리케이션에 대한 API 키를 생성합니다."""

        # 1. API 키가 이미 존재하는지 확인합니다.
        existingKey = self.get_key_by_app_id(appId)
        if existingKey:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="[api_key_repo] 이미 해당 애플리케이션에 대한 API 키가 존재합니다."
            )

        # 2. API 키를 생성합니다.
        key = secrets.token_hex(32)

        # 3. 만료 정책(일)에 따라 만료 시점(expiresAt)을 계산합니다.
        expiresAt = None  # 기본값은 None
        if expiresPolicy > 0:
            # 정책 값이 양수이면, 현재 시간에서 해당 일수만큼 더해 만료 시점을 설정합니다.
            expiresAt = datetime.now() + timedelta(days=expiresPolicy)

        # 4. API 키 객체를 생성합니다.
        key = AppApiKey(
            userId=userId,
            appId=appId,
            key=key,
            isActive=True,
            expiresAt=expiresAt
        )
        # 5. 데이터베이스에 API 키를 추가합니다.
        try:
            self.db.add(key)
            self.db.flush()  # 데이터베이스에 추가한 후, id를 할당받기 위해 flush합니다.
        except Exception as e:
            self.db.rollback()  # 오류 발생 시 롤백합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="[api_key_repo] API 키 생성 중 오류가 발생했습니다."
            )

        # 6. 새로 생성된 API 키 객체를 반환합니다.
        self.db.add(key)  # 데이터베이스에 추가합니다.
        self.db.commit()
        self.db.refresh(key)  # 최신 데이터를 가져옵니다.

        return key

    def get_keys_by_user_id(self, userId) -> List[AppApiKey]:
        """유저의 모든 API 키를 조회합니다."""

        return self.db.query(AppApiKey).filter(
            AppApiKey.userId == userId,
            AppApiKey.deletedAt.is_(None)
        ).all()

    def get_key_by_app_id(self, appId: int) -> AppApiKey:
        """특정 애플리케이션에 대한 API 키를 조회합니다."""

        return self.db.query(AppApiKey).filter(
            AppApiKey.appId == appId,
            AppApiKey.deletedAt.is_(None)
        ).first()

    def get_key_by_key_id(self, keyId: int) -> AppApiKey:
        """API 키 ID로 단일 API 키를 조회합니다."""

        return self.db.query(AppApiKey).filter(
            AppApiKey.id == keyId,
            AppApiKey.deletedAt.is_(None)
        ).first()

    def delete_key(self, keyId: int) -> AppApiKey:
        """API 키를 소프트 삭제합니다."""

        key = self.get_key_by_key_id(keyId)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="[api_key_repo] API 키를 찾을 수 없습니다."
            )

        key.deletedAt = datetime.now()
        key.isActive = False  # 비활성화 상태로 변경

        try:
            self.db.add(key)
            self.db.commit()  # 변경 사항을 커밋합니다.
        except Exception:
            self.db.rollback()  # 오류 발생 시 롤백합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="[api_key_repo] API 키 삭제 중 오류가 발생했습니다."
            )

        self.db.refresh(key)

        return key

    def activate_key(self, keyId: int) -> AppApiKey:
        """API 키를 활성화합니다."""

        key = self.get_key_by_key_id(keyId)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="[api_key_repo] API 키를 찾을 수 없습니다."
            )

        key.isActive = True

        try:
            self.db.add(key)
            self.db.commit()  # 변경 사항을 커밋합니다.
        except Exception:
            self.db.rollback()  # 오류 발생 시 롤백합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="[api_key_repo] API 키 활성화 중 오류가 발생했습니다."
            )

        self.db.refresh(key)

        return key

    def deactivate_key(self, keyId: int) -> AppApiKey:
        """API 키를 비활성화합니다."""

        key = self.get_key_by_key_id(keyId)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="[api_key_repo] API 키를 찾을 수 없습니다."
            )

        key.isActive = False

        try:
            self.db.add(key)
            self.db.commit()  # 변경 사항을 커밋합니다.
        except Exception:
            self.db.rollback()  # 오류 발생 시 롤백합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="[api_key_repo] API 키 비활성화 중 오류가 발생했습니다."
            )

        self.db.refresh(key)

        return key
