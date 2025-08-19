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

    #  애플리케이션 생성 CRUD
    def createApplication(self, userId: int,  appCreate: ApplicationCreate) -> Application:
        """새로운 애플리케이션을 생성합니다."""

        # 1. 애플리케이션 객체를 생성합니다.
        app = Application(
            userId=userId,
            appName=appCreate.appName,
            description=appCreate.description
        )

        # 2. 데이터베이스에 애플리케이션을 추가합니다.
        try:
            self.db.add(app)
            self.db.commit()  # 변경 사항을 커밋합니다.
        except Exception as e:
            self.db.rollback()  # 오류 발생 시 롤백합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="애플리케이션 생성 중 오류가 발생했습니다."
            )

        # 3. 새로 생성된 애플리케이션 객체를 반환합니다.
        self.db.add(app)  # 데이터베이스에 추가합니다.
        self.db.commit()  # 변경 사항을 커밋합니다.
        self.db.refresh(app)  # 최신 데이터를 가져옵니다.

        return app

    # 애플리케이션 조회 CRUD
    def getApplicationsByUserId(self, userId: int) -> List[Application]:
        """사용자의 모든 애플리케이션을 조회합니다."""

        return self.db.query(Application).filter(
            Application.userId == userId,
            Application.deletedAt.is_(None)
        ).all()

    # 애플리케이션 갯수 조회 CRUD
    def getApplicationsCountByUserId(self, userId: int) -> int:
        """사용자의 애플리케이션 개수를 조회합니다."""

        return self.db.query(Application).filter(
            Application.userId == userId,
            Application.deletedAt.is_(None)
        ).count()

    # 애플리케이션 단일 조회 CRUD
    def getApplicationByAppId(self, appId: int) -> Application:
        """애플리케이션 ID로 단일 애플리케이션을 조회합니다."""

        return self.db.query(Application).filter(
            Application.id == appId,
            Application.deletedAt.is_(None)
        ).first()

    # 애플리케이션 업데이트 CURD
    def updateApplication(self, app: Application, appUpdate: ApplicationUpdate) -> Application:
        """애플리케이션 정보를 업데이트합니다."""

        # 1. 애플리케이션 정보를 업데이트합니다.
        app.appName = appUpdate.appName
        app.description = appUpdate.description

        # 2. 업데이트된 애플리케이션을 데이터베이스에 추가합니다.
        try:
            self.db.add(app)
            self.db.commit()  # 변경 사항을 커밋합니다.
        except Exception:
            self.db.rollback()  # 오류 발생 시 롤백합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="애플리케이션 업데이트 중 오류가 발생했습니다."
            )

        # 3. 최신 데이터를 가져옵니다.
        self.db.refresh(app)

        return app

    # 애플리케이션 삭제 CRUD
    def deleteApplication(self, appId: int) -> Application:
        """애플리케이션을 소프트 삭제합니다."""

        app = self.getApplicationByAppId(appId)

        # 1. 애플리케이션의 삭제 시간을 현재 시간으로 설정합니다.
        app.deletedAt = datetime.now()

        # 2. 애플리케이션을 데이터베이스에 추가합니다.
        try:
            self.db.add(app)
            self.db.commit()  # 변경 사항을 커밋합니다.
        except Exception:
            self.db.rollback()  # 오류 발생 시 롤백합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="애플리케이션 삭제 중 오류가 발생했습니다."
            )

        # 3. 최신 데이터를 가져옵니다.
        self.db.refresh(app)

        return app
