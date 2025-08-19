# app/repositories/api_key_repo.py

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import secrets

from app.models.application import Application

from app.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def createKey(self, userId: int, appId: int, expiresPolicy: int = 0) -> ApiKey:
        """특정 애플리케이션에 대한 API 키를 새로 생성합니다."""
        # 1. 대상 애플리케이션을 조회합니다.
        application = self.db.query(Application).filter(
            Application.id == appId).first()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 ID의 애플리케이션을 찾을 수 없습니다."
            )

        # 2. 현재 활성화된 키가 있다면 에러를 반환합니다.
        if self.getKeyByAppId(appId):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 해당 애플리케이션에 대한 활성화된 API 키가 존재합니다."
            )

        # 3. 새로운 API 키를 생성합니다.
        new_key_str = secrets.token_hex(32)

        # 4. 만료 정책에 따라 만료 시점을 계산합니다.
        expiresAt = datetime.now() + timedelta(days=expiresPolicy) if expiresPolicy > 0 else None

        # 5. API 키 객체를 생성합니다.
        new_key = ApiKey(
            userId=userId,
            appId=appId,
            key=new_key_str,
            expiresAt=expiresAt,
            isActive=True  # 새로운 키는 활성화 상태로 생성
        )

        # 6. 데이터베이스에 변경사항을 커밋합니다.
        try:
            self.db.add(new_key)
            self.db.commit()
            self.db.refresh(new_key)
        except Exception as e:
            self.db.rollback()
            print(f"API 키 생성 중 오류 발생: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 생성 중 오류가 발생했습니다."
            )

        return new_key

    def deleteKeyByAppId(self, appId: int):
        """애플리케이션에 연결된 활성 API 키를 비활성화(soft-delete)합니다."""
        key = self.db.query(ApiKey).filter(
            ApiKey.appId == appId,
            ApiKey.deletedAt.is_(None)
        ).first()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 애플리케이션에 연결된 활성화된 API 키가 없습니다."
            )

        try:
            key.isActive = False
            key.deletedAt = datetime.now()
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 삭제 중 오류가 발생했습니다."
            )

    def getKeysByUserId(self, userId) -> List[ApiKey]:
        """유저의 모든 API 키를 조회합니다."""

        return self.db.query(ApiKey).filter(
            ApiKey.userId == userId,
            ApiKey.deletedAt.is_(None)
        ).all()

    def getKeyByAppId(self, appId: int) -> Optional[ApiKey]:
        """
        주어진 appId에 해당하는 현재 활성화된 API 키를 조회합니다.
        가장 최근에 생성된 활성화 키를 반환합니다.
        """
        return self.db.query(ApiKey).filter(
            and_(
                ApiKey.appId == appId,
                ApiKey.isActive == True,
                ApiKey.deletedAt.is_(None)
            )
        ).order_by(ApiKey.createdAt.desc()).first()

    def getKeyByKeyId(self, keyId: int) -> Optional[ApiKey]:
        """API 키 ID로 단일 API 키를 조회합니다."""

        return self.db.query(ApiKey).filter(
            ApiKey.id == keyId,
            ApiKey.deletedAt.is_(None)
        ).first()

    def deleteKey(self, keyId: int) -> Optional[ApiKey]:
        """API 키를 소프트 삭제합니다."""

        key = self.getKeyByKeyId(keyId)
        if not key:
            return None

        key.deletedAt = datetime.now()
        key.isActive = False

        try:
            self.db.add(key)
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 삭제 중 오류가 발생했습니다."
            )

        return key

    def activateKey(self, keyId: int) -> Optional[ApiKey]:
        """API 키를 활성화합니다."""

        key = self.getKeyByKeyId(keyId)
        if not key:
            return None
        key.isActive = True

        try:
            self.db.add(key)
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 활성화 중 오류가 발생했습니다."
            )

        return key

    def deactivateKey(self, keyId: int) -> Optional[ApiKey]:
        """API 키를 비활성화합니다."""

        key = self.getKeyByKeyId(keyId)
        if not key:
            return None
        key.isActive = False

        try:
            self.db.add(key)
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 비활성화 중 오류가 발생했습니다."
            )

        return key

    def getActiveApiKeyByTargetKey(self, targetKey: str) -> Optional[ApiKey]:
        """해당 키가 DB에 저장되어있는지 조회하고 유효한 키인지 검증합니다."""

        return self.db.query(ApiKey).filter(
            and_(
                ApiKey.key == targetKey,
                ApiKey.isActive == True,
                ApiKey.deletedAt.is_(None)
            )
        ).first()
