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
        """캡챠 문제를 생성하고 세션 정보를 반환하는 비즈니스 로직"""

        # 1. 사용자 토큰 잔액 확인 후 차감합니다.

        # "apiKey" 에 연결된 "User" 객체를 가져옵니다.
        user: User = apiKey.user

        # "user" 객체의 "token" 속성에 접근합니다.
        if user.token <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="API 토큰이 부족합니다."
            )

        user.token -= 1
        self.db.add(user)
        self.db.commit()

        # 2. 유효한 캡챠 문제를 무작위로 선택합니다.
        selectedProblem = self.captchaRepo.getRandomActiveProblem()
        if not selectedProblem:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="활성화된 캡차 문제가 없습니다."
            )

        # 3. 캡챠 세션을 생성합니다.

        # 클라이언트 토큰을 생성합니다.
        clientToken = str(uuid.uuid4())
        session = self.captchaRepo.createCaptchaSession(
            apiKeyId=apiKey.id,
            captchaProblemId=selectedProblem.id,
            clientToken=clientToken
        )

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
