# app/repositories/api_key_repo.py

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import secrets

from app.models.application import Application

from app.models.api_key import ApiKey, Difficulty


class ApiKeyRepository:
    def __init__(self, db: Session):
        """
        ApiKeyRepository의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db

    def createKey(self, userId: int, appId: int, expiresPolicy: int = 0, difficulty: Difficulty = Difficulty.MIDDLE) -> ApiKey:
        """
        특정 애플리케이션에 대한 새로운 API 키를 생성하고 데이터베이스에 저장합니다.

        Args:
            userId (int): API 키를 소유한 사용자의 ID.
            appId (int): API 키가 속한 애플리케이션의 ID.
            expiresPolicy (int, optional): 키 만료 정책(일 단위). 0 또는 음수이면 무제한. Defaults to 0.

        Returns:
            ApiKey: 새로 생성된 ApiKey 객체.
        """
        # 1. API 키를 발급할 대상 애플리케이션이 존재하는지 확인합니다.
        application = self.db.query(Application).filter(
            Application.id == appId).first()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 ID의 애플리케이션을 찾을 수 없습니다."
            )

        # 2. 해당 애플리케이션에 이미 활성화된 API 키가 있는지 확인합니다.
        if self.getKeyByAppId(appId):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 해당 애플리케이션에 대한 활성화된 API 키가 존재합니다."
            )

        # 3. `secrets` 모듈을 사용하여 암호학적으로 안전한 새 API 키 문자열을 생성합니다.
        new_key_str = secrets.token_hex(32)

        # 4. 만료 정책(expiresPolicy)에 따라 키의 만료 날짜를 계산합니다.
        # 정책 값이 0보다 크면 해당 일수만큼 유효 기간을 설정하고, 그렇지 않으면 만료되지 않도록 None으로 설정합니다.
        expiresAt = datetime.now() + timedelta(days=expiresPolicy) if expiresPolicy > 0 else None

        # 5. 새로운 ApiKey 모델 객체를 생성합니다.
        new_key = ApiKey(
            userId=userId,
            appId=appId,
            key=new_key_str,
            expiresAt=expiresAt,
            difficulty=difficulty,
            isActive=True  # 새로운 키는 기본적으로 활성화 상태입니다.
        )

        # 6. 생성된 API 키 객체를 데이터베이스 세션에 추가하고 커밋합니다.
        try:
            self.db.add(new_key)
            self.db.commit()
            # 7. 데이터베이스로부터 최신 상태(예: 자동 생성된 ID)를 객체에 반영합니다.
            self.db.refresh(new_key)
        except Exception as e:
            # 8. 오류 발생 시, 변경사항을 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            print(f"API 키 생성 중 오류 발생: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 생성 중 오류가 발생했습니다."
            )

        # 9. 최종적으로 생성된 ApiKey 객체를 반환합니다.
        return new_key

    def deleteKeyByAppId(self, appId: int):
        """
        특정 애플리케이션에 연결된 활성 API 키를 비활성화(소프트 삭제)합니다.

        Args:
            appId (int): API 키를 비활성화할 애플리케이션의 ID.
        """
        # 1. 주어진 애플리케이션 ID(appId)에 연결된, 아직 삭제되지 않은 API 키를 조회합니다.
        key = self.db.query(ApiKey).filter(
            ApiKey.appId == appId,
            ApiKey.deletedAt.is_(None)
        ).first()
        
        # 2. 비활성화할 키가 없으면 오류를 발생시킵니다.
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 애플리케이션에 연결된 활성화된 API 키가 없습니다."
            )

        try:
            # 3. 키의 상태를 비활성으로 변경하고, 삭제 시각을 현재 시간으로 기록합니다.
            key.isActive = False
            key.deletedAt = datetime.now()
            # 4. 변경사항을 데이터베이스에 커밋합니다.
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            # 5. 오류 발생 시, 변경사항을 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 삭제 중 오류가 발생했습니다."
            )

    def getKeysByUserId(self, userId: int) -> List[ApiKey]:
        """
        특정 사용자가 소유한 모든 활성 API 키 목록을 조회합니다.

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            List[ApiKey]: 해당 사용자의 모든 ApiKey 객체 리스트.
        """
        # 1. 사용자 ID(userId)를 기준으로, 아직 삭제되지 않은 모든 API 키를 조회하여 리스트로 반환합니다.
        return self.db.query(ApiKey).filter(
            ApiKey.userId == userId,
            ApiKey.deletedAt.is_(None)
        ).all()

    def getKeyByAppId(self, appId: int) -> Optional[ApiKey]:
        """
        애플리케이션 ID(appId)에 해당하는 현재 활성화된 API 키를 조회합니다.
        여러 개가 있을 경우 가장 최근에 생성된 키를 반환합니다.

        Args:
            appId (int): 조회할 애플리케이션의 ID.

        Returns:
            Optional[ApiKey]: 조회된 ApiKey 객체. 없으면 None을 반환합니다.
        """
        # 1. 애플리케이션 ID, 활성 상태(True), 삭제되지 않음 조건을 모두 만족하는 키를 조회합니다.
        # 2. 생성 시각(createdAt)을 기준으로 내림차순 정렬하여 가장 최근 키가 먼저 오도록 합니다.
        # 3. 첫 번째 결과(가장 최근 키)를 반환합니다.
        return self.db.query(ApiKey).filter(
            and_(
                ApiKey.appId == appId,
                ApiKey.isActive == True,
                ApiKey.deletedAt.is_(None)
            )
        ).order_by(ApiKey.createdAt.desc()).first()

    def getKeyByKeyId(self, keyId: int) -> Optional[ApiKey]:
        """
        API 키의 고유 ID(keyId)로 단일 API 키를 조회합니다.

        Args:
            keyId (int): 조회할 API 키의 ID.

        Returns:
            Optional[ApiKey]: 조회된 ApiKey 객체. 없으면 None을 반환합니다.
        """
        # 1. API 키 ID(id)와 삭제되지 않음 조건을 만족하는 키를 조회하여 반환합니다.
        return self.db.query(ApiKey).filter(
            ApiKey.id == keyId,
            ApiKey.deletedAt.is_(None)
        ).first()

    def deleteKey(self, keyId: int) -> Optional[ApiKey]:
        """
        API 키 ID(keyId)를 사용하여 API 키를 비활성화(소프트 삭제)합니다.

        Args:
            keyId (int): 비활성화할 API 키의 ID.

        Returns:
            Optional[ApiKey]: 비활성화된 ApiKey 객체. 대상 키가 없으면 None을 반환합니다.
        """
        # 1. 주어진 ID로 API 키를 조회합니다.
        key = self.getKeyByKeyId(keyId)
        # 2. 키가 존재하지 않으면 아무 작업도 하지 않고 None을 반환합니다.
        if not key:
            return None

        # 3. 키의 삭제 시각을 기록하고 비활성 상태로 변경합니다.
        key.deletedAt = datetime.now()
        key.isActive = False

        try:
            # 4. 변경사항을 데이터베이스 세션에 추가하고 커밋합니다.
            self.db.add(key)
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            # 5. 오류 발생 시, 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 삭제 중 오류가 발생했습니다."
            )
        
        # 6. 수정된 ApiKey 객체를 반환합니다.
        return key

    def activateKey(self, keyId: int) -> Optional[ApiKey]:
        """
        API 키 ID(keyId)를 사용하여 API 키를 활성화합니다.

        Args:
            keyId (int): 활성화할 API 키의 ID.

        Returns:
            Optional[ApiKey]: 활성화된 ApiKey 객체. 대상 키가 없으면 None을 반환합니다.
        """
        # 1. 주어진 ID로 API 키를 조회합니다.
        key = self.getKeyByKeyId(keyId)
        # 2. 키가 존재하지 않으면 아무 작업도 하지 않고 None을 반환합니다.
        if not key:
            return None
        
        # 3. 키를 활성 상태(isActive=True)로 변경합니다.
        key.isActive = True

        try:
            # 4. 변경사항을 데이터베이스에 커밋합니다.
            self.db.add(key)
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            # 5. 오류 발생 시, 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 활성화 중 오류가 발생했습니다."
            )

        # 6. 수정된 ApiKey 객체를 반환합니다.
        return key

    def deactivateKey(self, keyId: int) -> Optional[ApiKey]:
        """
        API 키 ID(keyId)를 사용하여 API 키를 비활성화합니다.

        Args:
            keyId (int): 비활성화할 API 키의 ID.

        Returns:
            Optional[ApiKey]: 비활성화된 ApiKey 객체. 대상 키가 없으면 None을 반환합니다.
        """
        # 1. 주어진 ID로 API 키를 조회합니다.
        key = self.getKeyByKeyId(keyId)
        # 2. 키가 존재하지 않으면 아무 작업도 하지 않고 None을 반환합니다.
        if not key:
            return None
        
        # 3. 키를 비활성 상태(isActive=False)로 변경합니다.
        key.isActive = False

        try:
            # 4. 변경사항을 데이터베이스에 커밋합니다.
            self.db.add(key)
            self.db.commit()
            self.db.refresh(key)
        except Exception:
            # 5. 오류 발생 시, 롤백하고 서버 오류를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API 키 비활성화 중 오류가 발생했습니다."
            )

        # 6. 수정된 ApiKey 객체를 반환합니다.
        return key

    def getActiveApiKeyByTargetKey(self, targetKey: str) -> Optional[ApiKey]:
        """
        API 키 문자열(targetKey)을 사용하여, 활성화되어 있고 유효한 API 키를 조회합니다.

        Args:
            targetKey (str): 검증할 API 키 문자열.

        Returns:
            Optional[ApiKey]: 조회된 ApiKey 객체. 유효하지 않으면 None을 반환합니다.
        """
        # 1. API 키 문자열, 활성 상태, 삭제되지 않음 조건을 모두 만족하는 키를 조회하여 반환합니다.
        return self.db.query(ApiKey).filter(
            and_(
                ApiKey.key == targetKey,
                ApiKey.isActive == True,
                ApiKey.deletedAt.is_(None)
            )
        ).first()

    def updateKey(self, key: ApiKey, keyUpdate: "ApiKeyUpdate") -> ApiKey:
        """
        API 키 정보를 업데이트합니다.

        Args:
            key (ApiKey): 업데이트할 API 키 객체.
            keyUpdate (ApiKeyUpdate): 업데이트할 정보가 담긴 스키마.

        Returns:
            ApiKey: 업데이트된 API 키 객체.
        """
        if keyUpdate.expiresPolicy is not None:
            expiresAt = datetime.now() + timedelta(days=keyUpdate.expiresPolicy) if keyUpdate.expiresPolicy > 0 else None
            key.expiresAt = expiresAt
        
        if keyUpdate.difficulty is not None:
            key.difficulty = keyUpdate.difficulty

        try:
            self.db.add(key)
            self.db.commit()
            self.db.refresh(key)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키 업데이트 중 오류가 발생했습니다: {e}"
            )

        return key