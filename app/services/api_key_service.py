from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..repositories.api_key_repo import AppApiKeyRepository
from ..models.api_key import AppApiKey
from ..models.user import User
from ..schemas.api_key import ApiKeyResponse


class ApiKeyService:
    def __init__(self, db: Session):
        self.db = db
        self.apiKeyRepo = AppApiKeyRepository(db)

    def create_key(self, currentUser: User, appId: int, expiresPolicy: int = 0) -> AppApiKey:
        """특정 애플리케이션에 대한 API 키를 생성합니다."""

        # 1. API 키가 이미 존재하는지 확인합니다.
        existingKey = self.apiKeyRepo.get_key_by_app_id(appId)
        if existingKey:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 해당 애플리케이션에 대한 API 키가 존재합니다."
            )

        # 2. API 키를 생성합니다.
        key: AppApiKey = self.apiKeyRepo.create_key(
            userId=currentUser.id,
            appId=appId,
            expiresPolicy=expiresPolicy
        )

        return key

    def get_keys(self, currentUser: User) -> List[ApiKeyResponse]:
        """현재 사용자의 모든 API 키를 조회합니다."""

        # 1. 사용자의 모든 API 키를 조회합니다.
        keys = self.apiKeyRepo.get_keys_by_user_id(currentUser.id)

        # 2. API 키가 없는 경우 예외 처리
        # if not keys:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail="API 키를 찾을 수 없습니다."
        #     )

        return keys

    def get_key(self, keyId: int, currentUser: User) -> ApiKeyResponse:
        """API 키 ID로 단일 API 키를 조회합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.get_key_by_key_id(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key or key.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        return key

    def delete_key(self, keyId: int, currentUser: User) -> ApiKeyResponse:
        """API 키를 소프트 삭제합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.get_key_by_key_id(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key or key.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        # 3. API 키를 삭제합니다.
        self.apiKeyRepo.delete_key(keyId)

        return key

    def activate_key(self, keyId: int) -> AppApiKey:
        """API 키를 활성화합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.get_key_by_key_id(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        # 3. API 키를 활성화합니다.
        return self.apiKeyRepo.activate_key(keyId)

    def deactivate_key(self, keyId: int) -> AppApiKey:
        """API 키를 비활성화합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.get_key_by_key_id(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        # 3. API 키를 비활성화합니다.
        return self.apiKeyRepo.deactivate_key(keyId)
