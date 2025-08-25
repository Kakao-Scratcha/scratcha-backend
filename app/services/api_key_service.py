from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.api_key_repo import ApiKeyRepository
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyResponse


class ApiKeyService:
    def __init__(self, db: Session):
        """
        ApiKeyService의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db
        self.apiKeyRepo = ApiKeyRepository(db)

    def createKey(self, currentUser: User, appId: int, expiresPolicy: int = 0) -> ApiKey:
        """
        특정 애플리케이션에 대한 새로운 API 키를 생성합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.
            appId (int): API 키를 생성할 애플리케이션의 ID.
            expiresPolicy (int, optional): 키 만료 정책(일 단위). 0 또는 음수이면 무제한. Defaults to 0.

        Returns:
            ApiKey: 새로 생성된 ApiKey 객체.
        """
        try:
            # 1. 해당 애플리케이션에 이미 활성화된 API 키가 존재하는지 확인합니다.
            existingKey = self.apiKeyRepo.getKeyByAppId(appId)
            if existingKey:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 해당 애플리케이션에 대한 활성화된 API 키가 존재합니다."
                )

            # 2. ApiKeyRepository를 통해 새로운 API 키를 생성합니다.
            key: ApiKey = self.apiKeyRepo.createKey(
                userId=currentUser.id,
                appId=appId,
                expiresPolicy=expiresPolicy
            )
            # 3. 생성된 API 키 객체를 반환합니다.
            return key
        except HTTPException as e:
            # 4. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 5. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키 생성 중 오류가 발생했습니다: {e}"
            )

    def getKeys(self, currentUser: User) -> List[ApiKeyResponse]:
        """
        현재 사용자가 소유한 모든 API 키 목록을 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            List[ApiKeyResponse]: 사용자의 모든 ApiKeyResponse 객체 리스트.
        """
        try:
            # 1. ApiKeyRepository를 통해 사용자의 모든 API 키를 조회합니다.
            keys = self.apiKeyRepo.getKeysByUserId(currentUser.id)
            # 2. 조회된 API 키 목록을 반환합니다.
            return keys
        except Exception as e:
            # 3. 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키 목록 조회 중 오류가 발생했습니다: {e}"
            )

    def getKey(self, keyId: int, currentUser: User) -> ApiKeyResponse:
        """
        API 키 ID로 단일 API 키를 조회합니다.

        Args:
            keyId (int): 조회할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            ApiKeyResponse: 조회된 ApiKeyResponse 객체.
        """
        try:
            # 1. ApiKeyRepository를 통해 API 키를 조회합니다.
            key = self.apiKeyRepo.getKeyByKeyId(keyId)

            # 2. API 키가 없거나 현재 사용자의 소유가 아닌 경우 404 오류를 발생시킵니다.
            if not key or key.userId != currentUser.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API 키를 찾을 수 없습니다."
                )
            # 3. 조회된 API 키 객체를 반환합니다.
            return key
        except HTTPException as e:
            # 4. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 5. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키 조회 중 오류가 발생했습니다: {e}"
            )

    def deleteKey(self, keyId: int, currentUser: User) -> ApiKeyResponse:
        """
        API 키를 소프트 삭제합니다.

        Args:
            keyId (int): 삭제할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            ApiKeyResponse: 소프트 삭제된 ApiKeyResponse 객체.
        """
        try:
            # 1. ApiKeyRepository를 통해 API 키를 조회합니다.
            key = self.apiKeyRepo.getKeyByKeyId(keyId)

            # 2. API 키가 없거나 현재 사용자의 소유가 아닌 경우 404 오류를 발생시킵니다.
            if not key or key.userId != currentUser.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API 키를 찾을 수 없습니다."
                )

            # 3. ApiKeyRepository를 통해 API 키를 소프트 삭제합니다.
            deletedKey = self.apiKeyRepo.deleteKey(keyId)
            # 4. 삭제된 API 키 객체를 반환합니다.
            return deletedKey
        except HTTPException as e:
            # 5. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 6. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키 삭제 중 오류가 발생했습니다: {e}"
            )

    def activateKey(self, keyId: int, currentUser: User) -> ApiKey:
        """
        API 키를 활성화합니다.

        Args:
            keyId (int): 활성화할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            ApiKey: 활성화된 ApiKey 객체.
        """
        try:
            # 1. ApiKeyRepository를 통해 API 키를 조회합니다.
            key = self.apiKeyRepo.getKeyByKeyId(keyId)

            # 2. API 키가 없거나 현재 사용자의 소유가 아닌 경우 404 오류를 발생시킵니다.
            if not key or key.userId != currentUser.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API 키를 찾을 수 없습니다."
                )

            # 3. ApiKeyRepository를 통해 API 키를 활성화합니다.
            activatedKey = self.apiKeyRepo.activateKey(keyId)
            # 4. 활성화된 API 키 객체를 반환합니다.
            return activatedKey
        except HTTPException as e:
            # 5. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 6. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키 활성화 중 오류가 발생했습니다: {e}"
            )

    def deactivateKey(self, keyId: int, currentUser: User) -> ApiKey:
        """
        API 키를 비활성화합니다.

        Args:
            keyId (int): 비활성화할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            ApiKey: 비활성화된 ApiKey 객체.
        """
        try:
            # 1. ApiKeyRepository를 통해 API 키를 조회합니다.
            key = self.apiKeyRepo.getKeyByKeyId(keyId)

            # 2. API 키가 없거나 현재 사용자의 소유가 아닌 경우 404 오류를 발생시킵니다.
            if not key or key.userId != currentUser.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API 키를 찾을 수 없습니다."
                )

            # 3. ApiKeyRepository를 통해 API 키를 비활성화합니다.
            deactivatedKey = self.apiKeyRepo.deactivateKey(keyId)
            # 4. 비활성화된 API 키 객체를 반환합니다.
            return deactivatedKey
        except HTTPException as e:
            # 5. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 6. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키 비활성화 중 오류가 발생했습니다: {e}"
            )