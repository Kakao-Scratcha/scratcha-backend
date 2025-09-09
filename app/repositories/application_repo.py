# app/repositories/application_repo.py

from datetime import datetime
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def createApplication(self, userId: int,  appCreate: ApplicationCreate) -> Application:
        """
        사용자 ID와 생성 데이터를 기반으로 새로운 애플리케이션을 생성합니다.
        """
        # 1. Pydantic 스키마로부터 받은 데이터로 Application 모델 객체를 생성합니다.
        app = Application(
            userId=userId,
            appName=appCreate.appName,
            description=appCreate.description
        )
        self.db.add(app)
        self.db.flush()
        self.db.refresh(app)
        return app

    def getApplicationsByUserId(self, userId: int) -> List[Application]:
        """
        특정 사용자가 소유한 모든 활성 애플리케이션 목록을 조회합니다.
        """
        # 1. 사용자 ID(userId)를 기준으로, 아직 삭제되지 않은(deletedAt is None) 모든 애플리케이션을 조회하여 리스트로 반환합니다.
        return self.db.query(Application).filter(
            Application.userId == userId,
            Application.deletedAt.is_(None)
        ).all()

    def getApplicationsCountByUserId(self, userId: int) -> int:
        """
        특정 사용자가 소유한 활성 애플리케이션의 총 개수를 조회합니다.
        """
        # 1. 사용자 ID(userId)를 기준으로, 아직 삭제되지 않은 모든 애플리케이션의 개수를 세어 반환합니다.
        return self.db.query(Application).filter(
            Application.userId == userId,
            Application.deletedAt.is_(None)
        ).count()

    def getApplicationByAppId(self, appId: int) -> Application:
        """
        애플리케이션의 고유 ID(appId)로 단일 활성 애플리케이션을 조회합니다.
        """
        # 1. 애플리케이션 ID(id)와 삭제되지 않음 조건을 만족하는 애플리케이션을 조회하여 반환합니다.
        return self.db.query(Application).filter(
            Application.id == appId,
            Application.deletedAt.is_(None)
        ).first()

    def updateApplication(self, app: Application, appUpdate: ApplicationUpdate) -> Application:
        """
        기존 애플리케이션 객체의 정보를 수정합니다.
        """
        # 1. 업데이트 스키마(appUpdate)에 제공된 값들로 기존 애플리케이션 객체(app)의 속성을 갱신합니다.
        app.appName = appUpdate.appName
        app.description = appUpdate.description
        self.db.add(app)
        return app

    def deleteApplication(self, appId: int) -> Application:
        """
        애플리케이션 ID(appId)를 사용하여 애플리케이션을 비활성화(소프트 삭제)합니다.
        """
        # 1. 주어진 ID로 애플리케이션을 조회합니다.
        app = self.getApplicationByAppId(appId)

        # 2. 애플리케이션의 삭제 시각(deletedAt)을 현재 시간으로 설정하여 소프트 삭제 처리합니다.
        app.deletedAt = datetime.now()
        self.db.add(app)
        return app
