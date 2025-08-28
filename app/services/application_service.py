from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.models.user import User
from app.models.api_key import ApiKey
from app.models.application import Application
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.application_repo import ApplicationRepository
from app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate, CountResponse
from app.schemas.api_key import ApiKeyResponse
from app.core.config import settings # settings 객체 임포트


class ApplicationService:
    def __init__(self, db: Session):
        """
        ApplicationService의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db
        self.appRepo = ApplicationRepository(db)
        self.apiKeyRepo = ApiKeyRepository(db)

    def mapToApplicationResponse(self, app: Application, key: Optional[ApiKey]) -> ApplicationResponse:
        """
        애플리케이션과 API 키 정보를 ApplicationResponse 스키마로 매핑합니다.

        Args:
            app (Application): 매핑할 Application 모델 객체.
            key (Optional[ApiKey]): 매핑할 ApiKey 모델 객체. API 키가 없을 수도 있습니다.

        Returns:
            ApplicationResponse: 매핑된 ApplicationResponse 객체.
        """
        # 1. ApplicationResponse 객체를 생성하여 반환합니다.
        return ApplicationResponse(
            id=app.id,
            userId=app.userId,
            appName=app.appName,
            description=app.description,
            # 2. API 키 정보가 존재하면 ApiKeyResponse로 변환하여 포함하고, 없으면 None으로 설정합니다.
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
        """
        새로운 애플리케이션을 생성하고, 해당 애플리케이션에 대한 API 키를 발급합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.
            appCreate (ApplicationCreate): 생성할 애플리케이션의 데이터 (스키마).

        Returns:
            ApplicationResponse: 생성된 애플리케이션과 API 키 정보를 포함하는 응답 객체.
        """
        try:
            # 1. 사용자의 현재 구독 플랜에 따른 최대 애플리케이션 생성 개수를 확인합니다。
            maxApps = settings.MAX_APPLICATIONS_PER_USER.get(currentUser.plan.value)

            # 2. 유효하지 않은 구독 상태인 경우 오류를 발생시킵니다.
            if maxApps is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="유효하지 않은 구독 상태입니다."
                )

            # 3. 현재 사용자가 생성한 애플리케이션의 개수를 조회합니다.
            currentAppsCount = self.appRepo.getApplicationsCountByUserId(
                currentUser.id)

            # 4. 최대 애플리케이션 개수를 초과하는 경우 예외 처리합니다.
            if maxApps != -1 and currentAppsCount >= maxApps:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"현재 구독 플랜({currentUser.plan.value})으로는 최대 {maxApps}개의 애플리케이션만 생성할 수 있습니다."
                )

            # 5. ApplicationRepository를 통해 새로운 애플리케이션을 생성합니다.
            app = self.appRepo.createApplication(currentUser.id, appCreate)

            # 6. ApiKeyRepository를 통해 생성된 애플리케이션에 대한 API 키를 발급합니다.
            key = self.apiKeyRepo.createKey(
                userId=currentUser.id,
                appId=app.id,
                expiresPolicy=appCreate.expiresPolicy
            )

            # 7. 생성된 애플리케이션과 API 키 정보를 매핑하여 반환합니다.
            return self.mapToApplicationResponse(app, key)
        except HTTPException as e:
            # 8. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 9. 그 외 예외 발생 시 서버 오류를 반환합니다。
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 생성 중 오류가 발생했습니다: {e}"
            )

    def getApplications(self, currentUser: User) -> List[ApplicationResponse]:
        """
        현재 사용자가 소유한 모든 애플리케이션 목록을 조회합니다. 각 애플리케이션에 연결된 API 키 정보도 포함합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            List[ApplicationResponse]: 사용자의 모든 애플리케이션 및 API 키 정보를 포함하는 응답 객체 리스트.
        """
        try:
            # 1. ApplicationRepository를 통해 사용자의 모든 애플리케이션을 조회합니다.
            apps = self.appRepo.getApplicationsByUserId(currentUser.id)
            # 2. ApiKeyRepository를 통해 사용자의 모든 API 키를 조회합니다.
            keys = self.apiKeyRepo.getKeysByUserId(currentUser.id)

            # 3. 조회된 애플리케이션과 API 키 정보를 매핑하여 리스트로 반환합니다.
            # 각 애플리케이션에 해당하는 API 키를 찾아 매핑합니다.
            return [
                self.mapToApplicationResponse(app, next(
                    (key for key in keys if key.appId == app.id), None))
                for app in apps
            ]
        except Exception as e:
            # 4. 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 목록 조회 중 오류가 발생했습니다: {e}"
            )

    def getApplicationsCount(self, currentUser: User) -> CountResponse:
        """
        현재 사용자가 생성한 애플리케이션의 총 개수를 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            CountResponse: 애플리케이션의 총 개수를 포함하는 응답 객체.
        """
        try:
            # 1. ApplicationRepository를 통해 사용자의 애플리케이션 개수를 조회합니다。
            count = self.appRepo.getApplicationsCountByUserId(currentUser.id)
            # 2. 조회된 개수를 CountResponse 스키마로 래핑하여 반환합니다.
            return CountResponse(count=count)
        except Exception as e:
            # 3. 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 개수 조회 중 오류가 발생했습니다: {e}"
            )

    def getApplication(self, appId: int, currentUser: User) -> ApplicationResponse:
        """
        애플리케이션 ID로 단일 애플리케이션을 조회합니다.

        Args:
            appId (int): 조회할 애플리케이션의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            ApplicationResponse: 조회된 애플리케이션과 API 키 정보를 포함하는 응답 객체.
        """
        try:
            # 1. ApplicationRepository를 통해 애플리케이션을 조회합니다。
            app = self.appRepo.getApplicationByAppId(appId)
            # 2. ApiKeyRepository를 통해 해당 애플리케이션에 연결된 API 키를 조회합니다.
            key = self.apiKeyRepo.getKeyByAppId(appId)

            # 3. 애플리케이션이 없거나 현재 사용자의 소유가 아닌 경우 404 오류를 발생시킵니다.
            if not app or app.userId != currentUser.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="애플리케이션을 찾을 수 없습니다."
                )

            # 4. 조회된 애플리케이션과 API 키 정보를 매핑하여 반환합니다.
            return self.mapToApplicationResponse(app, key)
        except HTTPException as e:
            # 5. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 6. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 조회 중 오류가 발생했습니다: {e}"
            )

    def updateApplication(self, appId: int, currentUser: User, appUpdate: ApplicationUpdate) -> ApplicationResponse:
        """
        애플리케이션 ID에 해당하는 애플리케이션 정보를 업데이트합니다.

        Args:
            appId (int): 업데이트할 애플리케이션의 ID.
            currentUser (User): 현재 인증된 사용자 객체.
            appUpdate (ApplicationUpdate): 업데이트할 애플리케이션의 데이터 (스키마).

        Returns:
            ApplicationResponse: 업데이트된 애플리케이션과 API 키 정보를 포함하는 응답 객체.
        """
        try:
            # 1. ApplicationRepository를 통해 애플리케이션을 조회합니다.
            app = self.appRepo.getApplicationByAppId(appId)
            # 2. ApiKeyRepository를 통해 해당 애플리케이션에 연결된 API 키를 조회합니다.
            key = self.apiKeyRepo.getKeyByAppId(appId)

            # 3. 애플리케이션이 없거나 현재 사용자의 소유가 아닌 경우 404 오류를 발생시킵니다.
            if not app or app.userId != currentUser.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="애플리케이션을 찾을 수 없습니다."
                )

            # 4. ApplicationRepository를 통해 애플리케이션 정보를 업데이트합니다.
            updatedApp = self.appRepo.updateApplication(app, appUpdate)

            # 5. 업데이트된 애플리케이션과 API 키 정보를 매핑하여 반환합니다.
            return self.mapToApplicationResponse(updatedApp, key)
        except HTTPException as e:
            # 6. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 7. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 업데이트 중 오류가 발생했습니다: {e}"
            )

    def deleteApplication(self, appId: int, currentUser: User) -> ApplicationResponse:
        """
        애플리케이션 ID에 해당하는 애플리케이션을 소프트 삭제하고, 연결된 API 키를 비활성화합니다.

        Args:
            appId (int): 삭제할 애플리케이션의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            ApplicationResponse: 삭제 처리된 애플리케이션과 API 키 정보를 포함하는 응답 객체.
        """
        try:
            # 1. ApplicationRepository를 통해 애플리케이션을 조회합니다.
            app = self.appRepo.getApplicationByAppId(appId)

            # 2. 애플리케이션이 없거나 현재 사용자의 소유가 아닌 경우 404 오류를 발생시킵니다.
            if not app or app.userId != currentUser.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="애플리케이션을 찾을 수 없습니다."
                )

            # 3. 연결된 API 키를 조회합니다.
            key = self.apiKeyRepo.getKeyByAppId(appId)

            # 4. ApiKeyRepository를 통해 연결된 API 키를 소프트 삭제합니다.
            # 키가 존재하면 삭제하고, 삭제된 키 객체를 받습니다.
            deletedKey = self.apiKeyRepo.deleteKey(key.id) if key else None

            # 5. ApplicationRepository를 통해 애플리케이션을 소프트 삭제합니다。
            deletedApp = self.appRepo.deleteApplication(appId)

            # 6. 삭제 처리된 애플리케이션과 API 키 정보를 매핑하여 반환합니다.
            return self.mapToApplicationResponse(deletedApp, deletedKey)
        except HTTPException as e:
            # 7. HTTP 예외는 그대로 다시 발생시킵니다.
            raise e
        except Exception as e:
            # 8. 그 외 예외 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 삭제 중 오류가 발생했습니다: {e}"
            )