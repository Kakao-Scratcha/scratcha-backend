# dashboard_api/app/services/application_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from dashboard_api.app.models.api_key import AppApiKey
from dashboard_api.app.models.application import UserApplication
from dashboard_api.app.repositories.api_key_repo import AppApiKeyRepository
from dashboard_api.app.repositories.application_repo import ApplicationRepository
from dashboard_api.app.schemas.application import ApplicationCreate, ApplicationResponse
from dashboard_api.app.schemas.api_key import ApiKeyResponse

# 애플리케이션 최대 허용 개수 상수 정의
MAX_APPLICATIONS_PER_USER = 5


class ApplicationService:
    def __init__(self, db: Session):
        self.applicationRepo = ApplicationRepository(db)
        self.apiKeyRepo = AppApiKeyRepository(db)

    def map_to_application_response(self, app: UserApplication, apiKey: AppApiKey) -> ApplicationResponse:
        """UserApplication 및 AppApiKey 모델을 ApplicationResponse 스키마로 매핑합니다."""

        if apiKey:
            apiKeyResponse = ApiKeyResponse(
                id=apiKey.id,
                key=apiKey.key,
                isActive=apiKey.isActive,
                expiresAt=apiKey.expiresAt,
                createdAt=apiKey.createdAt
            )
        return ApplicationResponse(
            id=app.id,
            userId=app.userId,
            appName=app.appName,
            description=app.description,
            createdAt=app.createdAt,
            deletedAt=app.deletedAt,
            key=apiKeyResponse
        )

    # 애플리케이션 생성 CRUD (API 키 포함)
    def create_application(self, userId: str, appCreate: ApplicationCreate) -> ApplicationResponse:
        """애플리케이션을 생성하고, 동시에 API 키도 발급합니다."""

        # 사용자별 애플리케이션 개수 제한
        currentApplications = self.applicationRepo.get_applications_by_user_id(
            userId)

        if len(currentApplications) >= MAX_APPLICATIONS_PER_USER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"사용자의 애플리케이션 개수를 초과했습니다. 최대 {MAX_APPLICATIONS_PER_USER}개")

        # 애플리케이션 생성
        dbApp = self.applicationRepo.create_application(userId, appCreate)

        # 생성된 애플리케이션에 대한 API 키 생성
        dbApiKey = self.apiKeyRepo.create_api_key(userId, dbApp.id)

        return self.map_to_application_response(dbApp, dbApiKey)

    # 애플리케이션 조회 CRUD
    def get_applications_by_user_id(self, userId: str) -> List[ApplicationResponse]:
        """특정 사용자의 모든 애플리케이션을 조회합니다."""

        dbApps = self.applicationRepo.get_applications_by_user_id(userId)

        if not dbApps:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="애플리케이션을 찾을 수 없습니다.")

        return dbApps
