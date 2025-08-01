# dashboard_api/app/repositories/application_repo.py

from datetime import datetime
from typing import List
from sqlalchemy import and_
from sqlalchemy.orm import Session

from dashboard_api.app.models.application import UserApplication
from dashboard_api.app.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    #  애플리케이션 생성 CRUD
    def create_application(self, userId: str,  appCreate: ApplicationCreate) -> UserApplication:
        """새로운 애플리케이션을 생성합니다."""

        dbApp = UserApplication(
            userId=userId,
            appName=appCreate.appName,
            description=appCreate.description
        )
        self.db.add(dbApp)
        self.db.commit()
        self.db.refresh(dbApp)
        return dbApp

    # 애플리케이션 조회 CRUD
    def get_applications_by_user_id(self, userId: str) -> List[UserApplication]:
        """특정 사용자의 모든 애플리케이션을 조회합니다."""

        return self.db.query(UserApplication).filter(UserApplication.userId == userId).all()

    # def get_applications_by_id(self, appId: str, userId: str = None) -> Optional[UserApplication]:
    #     """
    #     특정 애플리케이션을 조회합니다.
    #     """
    #     query = self.db.query(UserApplication).filter(
    #         and_(UserApplication.id == appId,
    #              UserApplication.deleted_at == None)
    #     )
    #     if userId:
    #         query = query.filter(UserApplication.user_id == userId)
    #     return query.first()

    # 애플리케이션 업데이트 CRUD
    def update_application(self, dbApp: UserApplication, appUpdate: ApplicationUpdate) -> UserApplication:
        """애플리케이션 정보를 업데이트합ㄴ다."""

        updateData = appUpdate.model_dump(exclude_unset=True)
        for key, value in updateData.items():
            setattr(dbApp, key, value)

        self.db.add(dbApp)
        self.db.commit()
        self.db.refresh(dbApp)

        return dbApp

    # 애플리케이션 삭제 CRUD
    def delete_application(self, dbApp: UserApplication) -> UserApplication:
        """애플리케이션을 소프트 삭제합니다."""

        dbApp.deletedAt = datetime.now()

        self.db.add(dbApp)
        self.db.commit()
        self.db.refresh(dbApp)

        return dbApp
