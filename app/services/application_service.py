# services/application_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from app.models.user import User
from app.models.api_key import ApiKey
from app.models.application import Application
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.application_repo import ApplicationRepository
from app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate, CountResponse
from app.schemas.api_key import ApiKeyResponse

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
        self.apiKeyRepo = ApiKeyRepository(db)

    def mapToApplicationResponse(self, app: Application, key: ApiKey) -> ApplicationResponse:
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

    def createApplication(self, currentUser: User, appCreate: ApplicationCreate) -> ApplicationResponse:
        """애플리케이션과 API 키를 생성합니다."""

        # 1. 사용자가 구독한 요금제를 확인.
        maxApps = MAX_APPLICATIONS_PER_USER.get(currentUser.plan.value)

        if maxApps is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 구독 상태입니다."
            )

        # 2. 사용자의 애플리케이션 개수를 조회
        currentAppsCount = self.appRepo.getApplicationsCountByUserId(
            currentUser.id)

        # 3. 최대 애플리케이션 개수를 초과하는 경우 예외 처리
        if maxApps != -1 and currentAppsCount >= maxApps:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"현재 구독 플랜({currentUser.plan.value})로는 최대 {maxApps}개의 애플리케이션만 생성할 수 있습니다."
            )

        # 4. 애플리케이션을 생성합니다.
        app = self.appRepo.createApplication(currentUser.id, appCreate)

        # 5. API 키를 생성합니다.
        key = self.apiKeyRepo.createKey(
            userId=currentUser.id,
            appId=app.id,
            expiresPolicy=appCreate.expiresPolicy
        )

        return self.mapToApplicationResponse(app, key)

    def getApplications(self, currentUser: User) -> List[ApplicationResponse]:
        """사용자의 모든 애플리케이션을 조회합니다."""

        # 1. 사용자의 애플리케이션 목록을 조회
        apps = self.appRepo.getApplicationsByUserId(currentUser.id)
        keys = self.apiKeyRepo.getKeysByUserId(currentUser.id)

        # 2. 사용자의 애플리케이션이 없는 경우 예외 처리 -> 빈배열 반환으로 수정 (2025.08.11)
        # if not apps:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail="사용자의 애플리케이션을 찾을 수 없습니다."
        #     )

        return [
            self.mapToApplicationResponse(app, next(
                (key for key in keys if key.appId == app.id), None))
            for app in apps
        ]

    def getApplicationsCount(self, currentuser: User) -> CountResponse:
        """사용자가 생성한 애플리케이션의 수를 조회합니다."""

        count = self.appRepo.getApplicationsCountByUserId(currentuser.id)
        return CountResponse(count=count)

    def getApplication(self, appId: int, currentUser: User) -> ApplicationResponse:
        """애플리케이션 ID로 단일 애플리케이션을 조회합니다."""

        # 1. 애플리케이션을 조회합니다.
        app = self.appRepo.getApplicationByAppId(appId)
        key = self.apiKeyRepo.getKeyByAppId(appId)

        # 2. 애플리케이션이 없는 경우 예외 처리
        if not app or app.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="애플리케이션을 찾을 수 없습니다."
            )

        return self.mapToApplicationResponse(app, key)

    def updateApplication(self, appId: int, currentUser: User, appUpdate: ApplicationUpdate) -> ApplicationResponse:
        """애플리케이션 정보를 업데이트합니다."""

        # 1. 애플리케이션을 조회합니다.
        app = self.appRepo.getApplicationByAppId(appId)
        key = self.apiKeyRepo.getKeyByAppId(appId)

        # 2. 애플리케이션이 없는 경우 예외 처리
        if not app or app.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="애플리케이션을 찾을 수 없습니다."
            )

        # 3. 애플리케이션 정보를 업데이트합니다.
        updatedApp = self.appRepo.updateApplication(app, appUpdate)

        return self.mapToApplicationResponse(updatedApp, key)

    def deleteApplication(self, appId: int, currentUser: User) -> ApplicationResponse:
        """애플리케이션을 소프트 삭제하고 연결된 API 키를 비활성화합니다."""

        # 1. 애플리케이션을 조회합니다.
        app = self.appRepo.getApplicationByAppId(appId)
        key = self.apiKeyRepo.getKeyByAppId(appId)

        # 2. 애플리케이션이 없는 경우 예외 처리
        if not app or app.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="애플리케이션을 찾을 수 없습니다."
            )

        # 4. 연결된 API 키를 삭제합니다.
        if key:
            self.apiKeyRepo.deleteKey(key.id)

        # 3. 애플리케이션을 소프트 삭제합니다.
        self.appRepo.deleteApplication(appId)

        return self.mapToApplicationResponse(app, key)
