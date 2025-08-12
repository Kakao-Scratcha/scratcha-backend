# services/application_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from ..models.user import User
from ..models.api_key import AppApiKey
from ..models.application import Application
from ..repositories.api_key_repo import AppApiKeyRepository
from ..repositories.application_repo import ApplicationRepository
from ..schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate
from ..schemas.api_key import ApiKeyResponse
from .api_key_service import ApiKeyService

# 사용자 구독 상태에 따른 최대 애플리케이션 개수 설정
MAX_APPLICATIONS_PER_USER = {
    "free": 1,
    "starter": 3,
    "pro": 5,
    "enterprise": -1  # 무제한
}


class ApplicationService:
    def __init__(self, db: Session):
        # 데이터베이스 세션을 직접 참조하고, 리포지토리 인스턴스를 생성합니다.
        self.db = db
        self.appRepo = ApplicationRepository(db)
        self.apiKeyRepo = AppApiKeyRepository(db)

    def map_to_application_response(self, app: Application, key: AppApiKey) -> ApplicationResponse:
        """애플리케이션과 API 키 정보를 ApplicationResponse로 매핑합니다."""

        return ApplicationResponse(
            id=app.id,
            userId=app.userId,
            appName=app.appName,
            description=app.description,
            key=ApiKeyResponse(
                id=key.id,
                key=key.key,
                isActive=key.isActive,
                expiresAt=key.expiresAt,
                createdAt=key.createdAt,
                updatedAt=key.updatedAt,
                deletedAt=key.deletedAt
            ) if key else None,
            createdAt=app.createdAt,
            updatedAt=app.updatedAt,
            deletedAt=app.deletedAt
        )

    def create_application(self, currentUser: User, appCreate: ApplicationCreate) -> ApplicationResponse:
        """애플리케이션과 API 키를 생성합니다."""

        # 1. 사용자가 구독한 요금제를 확인.
        maxApps = MAX_APPLICATIONS_PER_USER.get(currentUser.subscribe.value)

        if maxApps is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 구독 상태입니다."
            )

        # 2. 사용자의 애플리케이션 개수를 조회
        currentAppsCount = self.appRepo.get_applications_count_by_user_id(
            currentUser.id)

        # 3. 최대 애플리케이션 개수를 초과하는 경우 예외 처리
        if maxApps != -1 and currentAppsCount >= maxApps:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"현재 구독 플랜({currentUser.subscribe.value})로는 최대 {maxApps}개의 애플리케이션만 생성할 수 있습니다."
            )

        # 4. 애플리케이션을 생성합니다.
        app = self.appRepo.create_application(currentUser.id, appCreate)

        # 5. API 키를 생성합니다.
        key = self.apiKeyRepo.create_key(
            userId=currentUser.id,
            appId=app.id,
            expiresPolicy=appCreate.expiresPolicy
        )

        return self.map_to_application_response(app, key)

    def get_applications(self, currentUser: User) -> List[ApplicationResponse]:
        """사용자의 모든 애플리케이션을 조회합니다."""

        # 1. 사용자의 애플리케이션 목록을 조회
        apps = self.appRepo.get_applications_by_user_id(currentUser.id)
        keys = self.apiKeyRepo.get_keys_by_user_id(currentUser.id)

        # 2. 사용자의 애플리케이션이 없는 경우 예외 처리 -> 빈배열 반환으로 수정 (2025.08.11)
        # if not apps:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail="사용자의 애플리케이션을 찾을 수 없습니다."
        #     )

        return [
            self.map_to_application_response(app, next(
                (key for key in keys if key.appId == app.id), None))
            for app in apps
        ]

    def get_application(self, appId: int, currentUser: User) -> ApplicationResponse:
        """애플리케이션 ID로 단일 애플리케이션을 조회합니다."""

        # 1. 애플리케이션을 조회합니다.
        app = self.appRepo.get_application_by_app_id(appId)
        key = self.apiKeyRepo.get_key_by_app_id(appId)

        # 2. 애플리케이션이 없는 경우 예외 처리
        if not app or app.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="애플리케이션을 찾을 수 없습니다."
            )

        return self.map_to_application_response(app, key)

    def update_application(self, appId: int, currentUser: User, appUpdate: ApplicationUpdate) -> ApplicationResponse:
        """애플리케이션 정보를 업데이트합니다."""

        # 1. 애플리케이션을 조회합니다.
        app = self.appRepo.get_application_by_app_id(appId)
        key = self.apiKeyRepo.get_key_by_app_id(appId)

        # 2. 애플리케이션이 없는 경우 예외 처리
        if not app or app.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="애플리케이션을 찾을 수 없습니다."
            )

        # 3. 애플리케이션 정보를 업데이트합니다.
        updatedApp = self.appRepo.update_application(app, appUpdate)

        return self.map_to_application_response(updatedApp, key)

    def delete_application(self, appId: int, currentUser: User) -> ApplicationResponse:
        """애플리케이션을 소프트 삭제하고 연결된 API 키를 비활성화합니다."""

        # 1. 애플리케이션을 조회합니다.
        app = self.appRepo.get_application_by_app_id(appId)
        key = self.apiKeyRepo.get_key_by_app_id(appId)

        # 2. 애플리케이션이 없는 경우 예외 처리
        if not app or app.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="애플리케이션을 찾을 수 없습니다."
            )

        # 3. 애플리케이션을 소프트 삭제합니다.
        self.appRepo.delete_application(appId)

        # 4. 연결된 API 키를 삭제합니다.
        self.apiKeyRepo.delete_key(key.id)

        return self.map_to_application_response(app, key)
