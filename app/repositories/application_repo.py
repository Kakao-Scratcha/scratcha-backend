# app/repositories/application_repo.py

from datetime import datetime
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationRepository:
    def __init__(self, db: Session):
        """
        ApplicationRepository의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db

    def createApplication(self, userId: int,  appCreate: ApplicationCreate) -> Application:
        """
        사용자 ID와 생성 데이터를 기반으로 새로운 애플리케이션을 생성합니다.

        Args:
            userId (int): 애플리케이션을 소유한 사용자의 ID.
            appCreate (ApplicationCreate): 생성할 애플리케이션의 데이터 (스키마).

        Returns:
            Application: 새로 생성된 Application 객체.
        """
        # 1. Pydantic 스키마로부터 받은 데이터로 Application 모델 객체를 생성합니다.
        app = Application(
            userId=userId,
            appName=appCreate.appName,
            description=appCreate.description
        )

        try:
            # 2. 생성된 객체를 데이터베이스 세션에 추가합니다.
            self.db.add(app)
            # 3. 변경 사항을 데이터베이스에 커밋합니다.
            self.db.commit()
            # 4. 데이터베이스로부터 최신 상태(예: 자동 생성된 ID)를 객체에 반영합니다.
            self.db.refresh(app)
        except Exception as e:
            # 5. 오류 발생 시, 변경사항을 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 생성 중 오류가 발생했습니다: {e}"
            )

        # 6. 최종적으로 생성된 Application 객체를 반환합니다.
        return app

    def getApplicationsByUserId(self, userId: int) -> List[Application]:
        """
        특정 사용자가 소유한 모든 활성 애플리케이션 목록을 조회합니다.

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            List[Application]: 해당 사용자의 모든 활성 Application 객체 리스트.
        """
        # 1. 사용자 ID(userId)를 기준으로, 아직 삭제되지 않은(deletedAt is None) 모든 애플리케이션을 조회하여 리스트로 반환합니다.
        return self.db.query(Application).filter(
            Application.userId == userId,
            Application.deletedAt.is_(None)
        ).all()

    def getApplicationsCountByUserId(self, userId: int) -> int:
        """
        특정 사용자가 소유한 활성 애플리케이션의 총 개수를 조회합니다.

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            int: 해당 사용자의 활성 애플리케이션 개수.
        """
        # 1. 사용자 ID(userId)를 기준으로, 아직 삭제되지 않은 모든 애플리케이션의 개수를 세어 반환합니다.
        return self.db.query(Application).filter(
            Application.userId == userId,
            Application.deletedAt.is_(None)
        ).count()

    def getApplicationByAppId(self, appId: int) -> Application:
        """
        애플리케이션의 고유 ID(appId)로 단일 활성 애플리케이션을 조회합니다.

        Args:
            appId (int): 조회할 애플리케이션의 ID.

        Returns:
            Application: 조회된 Application 객체. 없으면 None을 반환합니다.
        """
        # 1. 애플리케이션 ID(id)와 삭제되지 않음 조건을 만족하는 애플리케이션을 조회하여 반환합니다.
        return self.db.query(Application).filter(
            Application.id == appId,
            Application.deletedAt.is_(None)
        ).first()

    def updateApplication(self, app: Application, appUpdate: ApplicationUpdate) -> Application:
        """
        기존 애플리케이션 객체의 정보를 수정합니다.

        Args:
            app (Application): 수정할 기존 Application 객체.
            appUpdate (ApplicationUpdate): 적용할 새로운 데이터 (스키마).

        Returns:
            Application: 정보가 수정된 Application 객체.
        """
        # 1. 업데이트 스키마(appUpdate)에 제공된 값들로 기존 애플리케이션 객체(app)의 속성을 갱신합니다.
        app.appName = appUpdate.appName
        app.description = appUpdate.description

        try:
            # 2. 변경된 사항을 데이터베이스에 커밋합니다.
            # app 객체는 이미 세션에 의해 추적되고 있으므로, 다시 add 할 필요가 없습니다.
            self.db.commit()
            # 3. 데이터베이스로부터 최신 상태를 객체에 반영합니다.
            self.db.refresh(app)
        except Exception as e:
            # 4. 오류 발생 시, 변경사항을 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 업데이트 중 오류가 발생했습니다: {e}"
            )

        # 5. 수정된 Application 객체를 반환합니다.
        return app

    def deleteApplication(self, appId: int) -> Application:
        """
        애플리케이션 ID(appId)를 사용하여 애플리케이션을 비활성화(소프트 삭제)합니다.

        Args:
            appId (int): 비활성화할 애플리케이션의 ID.

        Returns:
            Application: 비활성화된 Application 객체.
        """
        # 1. 주어진 ID로 애플리케이션을 조회합니다.
        app = self.getApplicationByAppId(appId)

        # 2. 애플리케이션의 삭제 시각(deletedAt)을 현재 시간으로 설정하여 소프트 삭제 처리합니다.
        app.deletedAt = datetime.now()

        try:
            # 3. 변경사항을 데이터베이스에 커밋합니다.
            self.db.commit()
            # 4. 데이터베이스로부터 최신 상태를 객체에 반영합니다.
            self.db.refresh(app)
        except Exception as e:
            # 5. 오류 발생 시, 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"애플리케이션 삭제 중 오류가 발생했습니다: {e}"
            )

        # 6. 수정된 Application 객체를 반환합니다.
        return app