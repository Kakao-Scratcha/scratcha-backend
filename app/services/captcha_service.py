# backend/services/captcha_service.py

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timedelta
from typing import Optional
import os
import random
from app.core.config import settings

from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories.captcha_repo import CaptchaRepository
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.schemas.captcha import CaptchaProblemResponse, CaptchaVerificationRequest, CaptchaVerificationResponse
from app.models.captcha_log import CaptchaResult


class CaptchaService:
    def __init__(self, db: Session):
        """
        CaptchaService의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db
        self.captchaRepo = CaptchaRepository(db)

    def generateCaptchaProblem(self, apiKey: ApiKey, ipAddress: Optional[str], userAgent: Optional[str]) -> CaptchaProblemResponse:
        """
        새로운 캡챠 문제를 생성하고, 사용자 토큰을 차감하며, 캡챠 세션 정보를 반환하는 비즈니스 로직입니다.
        이 과정은 단일 트랜잭션으로 처리됩니다.

        Args:
            apiKey (ApiKey): 캡챠 문제를 요청한 API 키 객체.
            ipAddress (Optional[str]): 클라이언트의 IP 주소.
            userAgent (Optional[str]): 클라이언트의 User-Agent 정보.

        Returns:
            CaptchaProblemResponse: 생성된 캡챠 문제의 상세 정보 (클라이언트 토큰, 이미지 URL, 프롬프트, 선택지).
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

            # 4. 기존에 로그되지 않은 세션이 있다면 삭제합니다. (1:1 트랜잭션 유지)
            self.captchaRepo.deleteUnloggedSessionsByApiKey(apiKey.id)

            # 5. CaptchaRepository를 통해 활성화된 캡챠 문제 중 하나를 무작위로 선택합니다.
            selectedProblem = self.captchaRepo.getRandomActiveProblem(
                apiKey.difficulty)
            # 6. 유효한 캡챠 문제가 없는 경우 503 Service Unavailable 오류를 발생시킵니다.
            if not selectedProblem:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="활성화된 캡차 문제가 없습니다."
                )

            # 7. 고유한 클라이언트 토큰을 생성합니다.
            clientToken = str(uuid.uuid4())
            # 8. CaptchaRepository를 통해 새로운 캡챠 세션을 생성하고 세션에 추가합니다. (아직 커밋되지 않음)
            session = self.captchaRepo.createCaptchaSession(
                keyId=apiKey.id,
                captchaProblemId=selectedProblem.id,
                clientToken=clientToken,
                ipAddress=ipAddress,
                userAgent=userAgent
            )

            # 9. S3_BASE_URL 환경 변수를 가져와 전체 이미지 URL을 구성합니다.
            s3BaseUrl = settings.S3_BASE_URL
            if not s3BaseUrl:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="S3_BASE_URL 환경 변수가 설정되지 않았습니다."
                )

            # S3 이미지 키와 S3_BASE_URL을 조합하여 클라이언트가 직접 접근할 수 있는 전체 URL을 생성합니다.
            fullImageUrl = f"{s3BaseUrl}/{selectedProblem.imageUrl}"

            # 10. usage_stats_repo를 사용하여 요청 카운트를 업데이트합니다.
            usageStatsRepo = UsageStatsRepository(self.db)
            usageStatsRepo.incrementTotalRequests(apiKey.id)

            # 11. 사용자 토큰 차감 및 캡챠 세션 생성 등 모든 변경사항을 데이터베이스에 한 번에 커밋합니다.
            self.db.commit()

            # 12. 커밋된 세션 객체를 새로고침하여 최신 상태를 반영합니다.
            self.db.refresh(session)

            # 13. 클라이언트에게 반환할 CaptchaProblemResponse 객체를 생성하여 반환합니다.
            option_list = [
                selectedProblem.answer,
                selectedProblem.wrongAnswer1,
                selectedProblem.wrongAnswer2,
                selectedProblem.wrongAnswer3
            ]
            random.shuffle(option_list)

            return CaptchaProblemResponse(
                clientToken=session.clientToken,
                imageUrl=fullImageUrl,  # S3 직접 이미지 URL을 반환
                prompt=selectedProblem.prompt,
                options=option_list
            )
        except HTTPException as e:
            # 12. HTTP 예외가 발생한 경우, 데이터베이스 변경사항을 롤백하고 해당 예외를 다시 발생시킵니다.
            self.db.rollback()
            raise e
        except Exception as e:
            # 13. 그 외 예상치 못한 예외가 발생한 경우, 데이터베이스 변경사항을 롤백하고 500 Internal Server Error를 발생시킵니다.
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    def verifyCaptchaAnswer(self, clientToken: str, request: CaptchaVerificationRequest, ipAddress: Optional[str], userAgent: Optional[str]) -> CaptchaVerificationResponse:
        """
        제출된 캡챠 답변을 검증하고, 결과를 기록하는 비즈니스 로직입니다.

        Args:
            clientToken (str): 클라이언트로부터 헤더로 받은 고유 토큰.
            request (CaptchaVerificationRequest): 클라이언트가 제출한 캡챠 검증 요청 데이터.
            ipAddress (Optional[str]): 클라이언트의 IP 주소.
            userAgent (Optional[str]): 클라이언트의 User-Agent 정보.

        Returns:
            CaptchaVerificationResponse: 캡챠 검증 결과 (성공, 실패, 시간 초과).
        """
        try:
            session = self.captchaRepo.getCaptchaSessionByClientToken(
                clientToken)

            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="유효하지 않은 클라이언트 토큰입니다."
                )

            if self.captchaRepo.does_log_exist_for_session(session.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 검증된 토큰입니다."
                )

            if session.createdAt.tzinfo is None:
                session.createdAt = settings.TIMEZONE.localize(
                    session.createdAt)

            latency = datetime.now(settings.TIMEZONE) - session.createdAt
            if latency > timedelta(minutes=3):
                self.captchaRepo.createCaptchaLog(
                    session=session,
                    result=CaptchaResult.TIMEOUT,
                    latency_ms=int(latency.total_seconds() * 1000)
                )

                usageStatsRepo = UsageStatsRepository(self.db)
                usageStatsRepo.incrementVerificationResult(
                    session.keyId, CaptchaResult.TIMEOUT.value, int(latency.total_seconds() * 1000))

                self.db.commit()
                return CaptchaVerificationResponse(result="timeout", message="캡챠 세션이 만료되었습니다.")

            correct_answer = session.captchaProblem.answer
            is_correct = request.answer == correct_answer

            result = CaptchaResult.SUCCESS if is_correct else CaptchaResult.FAIL
            message = "캡챠 검증에 성공했습니다." if is_correct else "캡챠 검증에 실패했습니다."

            self.captchaRepo.createCaptchaLog(
                session=session,
                result=result,
                latency_ms=int(latency.total_seconds() * 1000)
            )

            usageStatsRepo = UsageStatsRepository(self.db)
            usageStatsRepo.incrementVerificationResult(
                session.keyId, result.value, int(latency.total_seconds() * 1000))

            self.db.commit()

            return CaptchaVerificationResponse(result=result.value, message=message)

        except HTTPException as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))