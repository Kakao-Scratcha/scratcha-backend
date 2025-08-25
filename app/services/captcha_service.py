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
        """
        CaptchaService의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db
        self.captchaRepo = CaptchaRepository(db)

    def generateCaptchaProblem(self, apiKey: ApiKey) -> CaptchaProblemResponse:
        """
        새로운 캡챠 문제를 생성하고, 사용자 토큰을 차감하며, 캡챠 세션 정보를 반환하는 비즈니스 로직입니다.
        이 과정은 단일 트랜잭션으로 처리됩니다.

        Args:
            apiKey (ApiKey): 캡챠 문제를 요청한 API 키 객체.

        Returns:
            CaptchaProblemResponse: 생성된 캡챠 문제의 상세 정보와 클라이언트 토큰.
        """
        try:
            # 1. API 키에 연결된 사용자(User) 객체를 조회하고, 비관적 잠금(with_for_update)을 적용하여 동시성 문제를 방지합니다.
            user: User = self.db.query(User).filter(
                User.id == apiKey.userId).with_for_update().first()

            # 2. 사용자 또는 사용자 토큰 잔액이 부족한 경우 402 Payment Required 오류를 발생시킵니다.
            if not user or user.token <= 0:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="API 토큰이 부족합니다."
                )

            # 3. 사용자의 토큰 잔액을 1 차감하고, 변경사항을 세션에 추가합니다.
            user.token -= 1
            self.db.add(user)

            # 4. CaptchaRepository를 통해 활성화된 캡챠 문제 중 하나를 무작위로 선택합니다.
            selectedProblem = self.captchaRepo.getRandomActiveProblem()
            # 5. 유효한 캡챠 문제가 없는 경우 503 Service Unavailable 오류를 발생시킵니다.
            if not selectedProblem:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="활성화된 캡차 문제가 없습니다."
                )

            # 6. 고유한 클라이언트 토큰을 생성합니다.
            clientToken = str(uuid.uuid4())
            # 7. CaptchaRepository를 통해 새로운 캡챠 세션을 생성하고 세션에 추가합니다. (아직 커밋되지 않음)
            session = self.captchaRepo.createCaptchaSession(
                keyId=apiKey.id,
                captchaProblemId=selectedProblem.id,
                clientToken=clientToken
            )

            # 8. 사용자 토큰 차감 및 캡챠 세션 생성 등 모든 변경사항을 데이터베이스에 한 번에 커밋합니다.
            self.db.commit()
            # 9. 커밋된 세션 객체를 새로고침하여 최신 상태를 반영합니다.
            self.db.refresh(session)

            # 10. 클라이언트에게 반환할 CaptchaProblemResponse 객체를 생성하여 반환합니다.
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
        except HTTPException as e:
            # 11. HTTP 예외가 발생한 경우, 데이터베이스 변경사항을 롤백하고 해당 예외를 다시 발생시킵니다.
            self.db.rollback()
            raise e
        except Exception as e:
            # 12. 그 외 예상치 못한 예외가 발생한 경우, 데이터베이스 변경사항을 롤백하고 500 Internal Server Error를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))