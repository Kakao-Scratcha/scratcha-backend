# dashboard_api/app/repositories/application_repo.py

from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from dashboard_api.app.models.application import Application
from dashboard_api.app.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    #  애플리케이션 생성 CRUD
    def create_application(self, userId: str,  appCreate: ApplicationCreate) -> Application:
        """새로운 애플리케이션을 생성합니다. commit은 서비스 계층에서 수행합니다."""

        dbApp = Application(
            userId=userId,
            appName=appCreate.appName,
            description=appCreate.description
        )

        self.db.add(dbApp)
        return dbApp

    # 애플리케이션 조회 CRUD
    def get_applications_by_user_id(self, userId: str) -> List[Application]:
        """특정 사용자의 모든 애플리케이션을 조회합니다."""

        return self.db.query(Application).filter(Application.userId == userId, Application.deletedAt.is_(None)).all()

    # 애플리케이션 단일 조회 CRUD
    def get_application_by_id(self, appId: str) -> Application:
        """애플리케이션 ID로 단일 애플리케이션을 조회합니다."""

        return self.db.query(Application).filter(Application.id == appId).first()

    # 애플리케이션 업데이트 CURD
    def update_application(self, dbApp: Application, appUpdate: ApplicationUpdate) -> Application:
        """애플리케이션 정보를 업데이트합니다. commit은 서비스 계층에서 수행합니다."""

        update_data = appUpdate.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(dbApp, key, value)

        self.db.add(dbApp)
        return dbApp

    # 애플리케이션 삭제 CRUD
    def delete_application(self, dbApp: Application) -> Application:
        """애플리케이션을 소프트 삭제합니다. commit은 서비스 계층에서 수행합니다."""

        dbApp.deletedAt = datetime.now()
        self.db.add(dbApp)
        return dbApp
