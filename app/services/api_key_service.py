from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.api_key_repo import ApiKeyRepository
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyResponse


class ApiKeyService:
    def __init__(self, db: Session):
        self.db = db
        self.apiKeyRepo = ApiKeyRepository(db)

    def createKey(self, currentUser: User, appId: int, expiresPolicy: int = 0) -> ApiKey:
        """특정 애플리케이션에 대한 API 키를 생성합니다."""

        # 1. API 키가 이미 존재하는지 확인합니다.
        existingKey = self.apiKeyRepo.getKeyByAppId(appId)
        if existingKey:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 해당 애플리케이션에 대한 API 키가 존재합니다."
            )

        # 2. API 키를 생성합니다.
        key: ApiKey = self.apiKeyRepo.createKey(
            userId=currentUser.id,
            appId=appId,
            expiresPolicy=expiresPolicy
        )

        return key

    def getKeys(self, currentUser: User) -> List[ApiKeyResponse]:
        """현재 사용자의 모든 API 키를 조회합니다."""

        # 1. 사용자의 모든 API 키를 조회합니다.
        keys = self.apiKeyRepo.getKeysByUserId(currentUser.id)

        # 2. API 키가 없는 경우 예외 처리
        # if not keys:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail="API 키를 찾을 수 없습니다."
        #     )

        return keys

    def getKey(self, keyId: int, currentUser: User) -> ApiKeyResponse:
        """API 키 ID로 단일 API 키를 조회합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.getKeyByKeyId(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key or key.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        return key

    def deleteKey(self, keyId: int, currentUser: User) -> ApiKeyResponse:
        """API 키를 소프트 삭제합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.getKeyByKeyId(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key or key.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        # 3. API 키를 삭제합니다.
        self.apiKeyRepo.deleteKey(keyId)

        return key

    def activateKey(self, keyId: int) -> ApiKey:
        """API 키를 활성화합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.getKeyByKeyId(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        # 3. API 키를 활성화합니다.
        return self.apiKeyRepo.activateKey(keyId)

    def deactivateKey(self, keyId: int) -> ApiKey:
        """API 키를 비활성화합니다."""

        # 1. API 키를 조회합니다.
        key = self.apiKeyRepo.getKeyByKeyId(keyId)

        # 2. API 키가 없는 경우 예외 처리
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API 키를 찾을 수 없습니다."
            )

        # 3. API 키를 비활성화합니다.
        return self.apiKeyRepo.deactivateKey(keyId)
