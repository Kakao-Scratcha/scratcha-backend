# dashboard_api/app/services/application_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from dashboard_api.app.models.user import User
from dashboard_api.app.models.api_key import AppApiKey
from dashboard_api.app.models.application import Application
from dashboard_api.app.repositories.api_key_repo import AppApiKeyRepository
from dashboard_api.app.repositories.application_repo import ApplicationRepository
from dashboard_api.app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate
from dashboard_api.app.schemas.api_key import ApiKeyResponse

# 애플리케이션 최대 허용 개수 상수 정의
# TODO: 후에 요금제별로 생성 가능한 애플리케이션 개수를 조정할 수 있도록 변경
MAX_APPLICATIONS_PER_USER = 5


class ApplicationService:
    def __init__(self, db: Session):
        # 데이터베이스 세션을 직접 참조하고, 리포지토리 인스턴스를 생성합니다.
        self.db = db
        self.appRepo = ApplicationRepository(db)
        self.apiKeyRepo = AppApiKeyRepository(db)

    def map_to_application_response(self, app: Application, apiKey: AppApiKey) -> ApplicationResponse:
        """Application 및 AppApiKey 모델을 ApplicationResponse 스키마로 매핑합니다."""

        # API 키가 존재하지 않는 경우 None으로 설정
        apiKeyResponse = None
        if apiKey:
            apiKeyResponse = ApiKeyResponse(
                id=apiKey.id,
                key=apiKey.key,
                isActive=apiKey.isActive,
                createdAt=apiKey.createdAt,
                expiresAt=apiKey.expiresAt,
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

    def _get_and_validate_application(self, appId: str, currentUser: User) -> Application:
        """ID로 앱을 조회하고 사용자가 소유자인지 확인합니다."""
        app = self.appRepo.get_application_by_id(appId)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="애플리케이션을 찾을 수 없습니다."
            )
        if app.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 애플리케이션에 대한 접근 권한이 없습니다."
            )
        return app

    def create_application(self, currentUser: User, appCreate: ApplicationCreate) -> ApplicationResponse:
        """애플리케이션과 API 키를 원자적으로 생성합니다."""

        # 사용자별 애플리케이션 개수 제한
        apps = self.appRepo.get_applications_by_user_id(currentUser.id)
        if len(apps) >= MAX_APPLICATIONS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"사용자의 애플리케이션 개수를 초과했습니다. 최대 {MAX_APPLICATIONS_PER_USER}개"
            )

        # 애플리케이션 객체 생성 (메모리)
        app = self.appRepo.create_application(currentUser.id, appCreate)

        # 변경사항을 flush하여 데이터베이스로부터 app.id를 할당받음
        # 트랜잭션은 아직 열려있어 오류 발생 시 전체 롤백 가능
        self.db.flush()

        # API 키 객체 생성 (메모리)
        apiKey = self.apiKeyRepo.create_api_key(
            userId=currentUser.id, applicationId=app.id, expiration_policy_days=appCreate.expirationPolicy)

        try:
            # 모든 변경사항을 한번에 커밋
            self.db.commit()
        except Exception as e:
            # 커밋 중 오류 발생 시 롤백하여 데이터 일관성 유지
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"데이터베이스 처리 중 오류가 발생했습니다: {e}"
            )

        # 데이터베이스의 최신 상태를 객체에 반영
        self.db.refresh(app)
        self.db.refresh(apiKey)

        return self.map_to_application_response(app, apiKey)

    def get_applications(self, currentUser: User) -> List[ApplicationResponse]:
        """특정 사용자의 모든 애플리케이션을 조회합니다."""

        # 사용자의 애플리케이션 목록을 조회
        apps = self.appRepo.get_applications_by_user_id(currentUser.id)

        # 사용자의 애플리케이션이 없는 경우 예외 처리
        if not apps:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자의 애플리케이션을 찾을 수 없습니다."
            )

        # 각 애플리케이션에 대한 API 키 조회 및 매핑
        appResponses = []
        for app in apps:
            apiKey = self.apiKeyRepo.get_api_key_by_app_id(app.id)
            appResponses.append(
                self.map_to_application_response(app, apiKey))

        return appResponses

    def get_application(self, appId: str, currentUser: User) -> ApplicationResponse:
        """애플리케이션 ID로 단일 애플리케이션을 조회합니다."""
        app = self._get_and_validate_application(appId, currentUser)
        apiKey = self.apiKeyRepo.get_api_key_by_app_id(app.id)
        return self.map_to_application_response(app, apiKey)

    def update_application(self, appId: str, currentUser: User, appUpdate: ApplicationUpdate) -> ApplicationResponse:
        """애플리케이션 정보를 원자적으로 업데이트합니다."""
        app = self._get_and_validate_application(appId, currentUser)

        # 업데이트할 필드가 없으면 오류 발생
        if not appUpdate.dict(exclude_unset=True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업데이트할 필드를 지정해야 합니다."
            )

        # 애플리케이션 정보 업데이트 (메모리)
        updatedApp = self.appRepo.update_application(app, appUpdate)
        apiKey = self.apiKeyRepo.get_api_key_by_app_id(updatedApp.id)

        try:
            # 변경사항을 커밋
            self.db.commit()
        except Exception as e:
            # 커밋 중 오류 발생 시 롤백
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"데이터베이스 처리 중 오류가 발생했습니다: {e}"
            )

        # 최신 상태를 객체에 반영
        self.db.refresh(updatedApp)
        if apiKey:
            self.db.refresh(apiKey)

        return self.map_to_application_response(updatedApp, apiKey)

    def delete_application(self, appId: str, currentUser: User) -> ApplicationResponse:
        """애플리케이션을 소프트 삭제하고 연결된 API 키를 비활성화합니다."""
        app = self._get_and_validate_application(appId, currentUser)

        # 연결된 API 키를 조회합니다.
        apiKey = self.apiKeyRepo.get_api_key_by_app_id(app.id)

        # API 키가 존재하면 비활성화합니다.
        if apiKey:
            self.apiKeyRepo.deactivate_api_key(apiKey)

        # 애플리케이션을 소프트 삭제합니다.
        deleted_app = self.appRepo.delete_application(app)

        # 서비스 계층에서 모든 변경사항을 한번에 커밋합니다.
        self.db.commit()

        # 커밋 후, 데이터베이스의 최종 상태를 객체에 반영합니다.
        self.db.refresh(deleted_app)
        if apiKey:
            self.db.refresh(apiKey)

        # 삭제된 애플리케이션과 최종 상태의 API 키 정보를 함께 반환합니다.
        return self.map_to_application_response(deleted_app, apiKey)
