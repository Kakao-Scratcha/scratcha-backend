# backend/services/captcha_service.py

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import uuid


from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories.captcha_repo import CaptchaRepository
from app.schemas.captcha import CaptchaProblemResponse


class CaptchaService:
    def __init__(self, db: Session):
        self.db = db
        self.captchaRepo = CaptchaRepository(db)

    def generateCaptchaProblem(self, apiKey: ApiKey) -> CaptchaProblemResponse:
        """캡챠 문제를 생성하고 세션 정보를 반환하는 비즈니스 로직 (트랜잭션 적용)"""
        try:
            # 1. 사용자 토큰 잔액 확인 후 차감 (with_for_update() : 비관적 잠금 적용)
            # apiKey에 연결된 User 객체를 가져옵니다.
            user: User = self.db.query(User).filter(
                User.id == apiKey.userId).with_for_update().first()

            if not user or user.token <= 0:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="API 토큰이 부족합니다."
                )

            user.token -= 1
            self.db.add(user)

            # 2. 유효한 캡챠 문제를 무작위로 선택합니다.
            selectedProblem = self.captchaRepo.getRandomActiveProblem()
            if not selectedProblem:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="활성화된 캡차 문제가 없습니다."
                )

            # 3. 캡챠 세션을 생성합니다. (커밋 없음)
            clientToken = str(uuid.uuid4())
            session = self.captchaRepo.createCaptchaSession(
                keyId=apiKey.id,
                captchaProblemId=selectedProblem.id,
                clientToken=clientToken
            )

            # 4. 모든 변경사항을 한 번에 커밋합니다.
            self.db.commit()
            self.db.refresh(session)

            return CaptchaProblemResponse(
                clientToken=session.clientToken,
                imageUrl=selectedProblem.imageUrl,
                prompt=selectedProblem.prompt,
                options=[
                    selectedProblem.answer,
                    selectedProblem.wrongAnswer1,
                    selectedProblem.wrongAnswer2,
                    selectedProblem.wrongAnswer3
                ]
            )
        except Exception as e:
            # 5. 오류 발생 시 모든 변경사항을 롤백합니다.
            self.db.rollback()
            # HTTP 예외는 그대로 전달하고, 그 외의 예외는 500 에러로 처리합니다.
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
