# app/services/captcha_service.py

import logging
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import uuid
import random

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories.captcha_repo import CaptchaRepository
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.schemas.captcha import CaptchaProblemResponse, CaptchaVerificationRequest, CaptchaVerificationResponse
from app.models.captcha_log import CaptchaResult
from app.services import behavior_service

# 로거 설정
logger = logging.getLogger(__name__)


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

            # 4. CaptchaRepository를 통해 활성화된 캡챠 문제 중 하나를 무작위로 선택합니다.
            selectedProblem = self.captchaRepo.getRandomActiveProblem(
                apiKey.difficulty)
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
                clientToken=clientToken,
                ipAddress=ipAddress,
                userAgent=userAgent
            )

            # 8. S3_BASE_URL 환경 변수를 가져와 전체 이미지 URL을 구성합니다.
            s3BaseUrl = settings.KS3_BASE_URL
            if not s3BaseUrl:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="KS3_BASE_URL 환경 변수가 설정되지 않았습니다."  # Changed from S3_BASE_URL
                )

            # S3 이미지 키와 S3_BASE_URL을 조합하여 클라이언트가 직접 접근할 수 있는 전체 URL을 생성합니다.
            fullImageUrl = f"{s3BaseUrl}/{selectedProblem.imageUrl}"

            # 9. usage_stats_repo를 사용하여 요청 카운트를 업데이트합니다.
            usageStatsRepo = UsageStatsRepository(self.db)
            usageStatsRepo.incrementTotalRequests(apiKey.id)

            # 10. 사용자 토큰 차감 및 캡챠 세션 생성 등 모든 변경사항을 데이터베이스에 한 번에 커밋합니다.
            self.db.commit()

            # 11. 커밋된 세션 객체를 새로고침하여 최신 상태를 반영합니다.
            self.db.refresh(session)

            # 12. 클라이언트에게 반환할 CaptchaProblemResponse 객체를 생성하여 반환합니다.
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
            # 13. HTTP 예외가 발생한 경우, 데이터베이스 변경사항을 롤백하고 해당 예외를 다시 발생시킵니다.
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    def verifyCaptchaAnswer(
        self,
        clientToken: str,
        request: CaptchaVerificationRequest,
        ipAddress: Optional[str],
        userAgent: Optional[str]
    ) -> CaptchaVerificationResponse:
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
        # 순환 참조를 방지하기 위해 함수 내에서 task를 임포트합니다.
        from app.tasks.captcha_tasks import uploadBehaviorDataTask

        try:
            # 1. 클라이언트 토큰을 사용하여 캡챠 세션 정보를 데이터베이스에서 조회합니다.
            session = self.captchaRepo.getCaptchaSessionByClientToken(
                clientToken, for_update=True)

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

            # 행동 데이터 업로드를 비동기 작업으로 처리
            if settings.ENABLE_KS3:
                uploadBehaviorDataTask.delay(clientToken, request.dict())

            if session.createdAt.tzinfo is None:
                session.createdAt = settings.TIMEZONE.localize(
                    session.createdAt)

            latency = datetime.now(settings.TIMEZONE) - session.createdAt
            if latency > timedelta(minutes=settings.CAPTCHA_TIMEOUT_MINUTES):
                self.captchaRepo.createCaptchaLog(
                    session=session,
                    result=CaptchaResult.TIMEOUT,
                    latency_ms=int(latency.total_seconds() * 1000),
                    is_correct=False,  # Timeout implies incorrect
                    ml_confidence=None,
                    ml_is_bot=None
                )
                usageStatsRepo = UsageStatsRepository(self.db)
                usageStatsRepo.incrementVerificationResult(
                    session.keyId, CaptchaResult.TIMEOUT.value, int(latency.total_seconds() * 1000))
                self.db.commit()
                return CaptchaVerificationResponse(result="timeout", message="캡챠 세션이 만료되었습니다.")

            # 행동 데이터 분석
            confidence = None
            verdict = None
            if request.meta and request.events:
                logger.debug(f"행동 데이터 메타: {request.meta}")
                logger.debug(f"행동 이벤트: {request.events}")
                behavior_result = behavior_service.run_behavior_verification(
                    request.meta, request.events)
                logger.debug(f"행동 분석 결과: {behavior_result}")
                if behavior_result and behavior_result.get("ok"):
                    confidence = behavior_result.get("bot_prob")
                    verdict = behavior_result.get("verdict")
                    logger.debug(
                        f"할당된 신뢰도: {confidence}, 판정: {verdict}")

            # 7. 세션에 연결된 캡챠 문제의 정답을 가져옵니다.
            correct_answer = session.captchaProblem.answer
            # 8. 사용자가 제출한 답변과 정답을 비교하여 성공 여부를 판단합니다.
            is_correct = request.answer == correct_answer

            # 9. 성공 여부에 따라 결과(SUCCESS/FAIL)와 메시지를 설정합니다.
            # result = CaptchaResult.SUCCESS if is_correct else CaptchaResult.FAIL # Old logic
            if is_correct and verdict == "human":
                result = CaptchaResult.SUCCESS
                message = "캡챠 검증에 성공했습니다."
            else:
                result = CaptchaResult.FAIL
                message = "캡챠 검증에 실패했습니다."

            # 10. 검증 결과를 로그에 기록합니다.
            self.captchaRepo.createCaptchaLog(
                session=session,
                result=result,
                latency_ms=int(latency.total_seconds() * 1000),
                is_correct=is_correct,
                ml_confidence=confidence,
                # Convert verdict to boolean
                ml_is_bot=(verdict == "bot") if verdict else None
            )

            # 11. API 키 사용 통계에 검증 결과를 업데이트합니다.
            usageStatsRepo = UsageStatsRepository(self.db)
            usageStatsRepo.incrementVerificationResult(
                session.keyId, result.value, int(latency.total_seconds() * 1000))

            # 12. 모든 변경사항(로그 기록, 통계 업데이트)을 하나의 트랜잭션으로 데이터베이스에 커밋합니다.
            self.db.commit()

            # 13. 최종 검증 결과를 클라이언트에게 반환합니다.
            return CaptchaVerificationResponse(result=result.value, message=message, confidence=confidence, verdict=verdict)

        except HTTPException as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
