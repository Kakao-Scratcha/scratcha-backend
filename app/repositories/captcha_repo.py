# app/repositories/captcha_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta
import random
from fastapi import HTTPException, status

from app.models.captcha_problem import CaptchaProblem
from app.models.captcha_session import CaptchaSession
from app.models.captcha_log import CaptchaLog, CaptchaResult
from app.core.config import settings  # settings 객체 임포트
from app.models.api_key import Difficulty


class CaptchaRepository:
    def __init__(self, db: Session):
        self.db = db

    def getRandomActiveProblem(self, difficulty: Optional[Difficulty] = None) -> Optional[CaptchaProblem]:
        """
        데이터베이스에서 활성화된 (만료되지 않은) 캡챠 문제 중 하나를 무작위로 선택하여 반환합니다.
        """
        try:
            # 1. 현재 시간을 기준으로 아직 만료되지 않은 모든 캡챠 문제를 데이터베이스에서 조회합니다.
            # DB의 타임존 설정과 무관하게 애플리케이션의 타임존 설정을 기준으로 현재 시간을 계산합니다.
            query = self.db.query(CaptchaProblem).filter(
                CaptchaProblem.expiresAt > datetime.now(settings.TIMEZONE)
            )

            if difficulty is not None:
                query = query.filter(
                    CaptchaProblem.difficulty == difficulty.to_int())

            validProblems = query.all()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류가 발생하면 서버 오류를 발생시킵니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"캡챠 문제 조회 중 오류가 발생했습니다: {e}"
            )

        # 3. 유효한 문제가 없는 경우, None을 반환합니다.
        if not validProblems:
            return None

        # 4. 조회된 유효한 문제 목록에서 무작위로 하나를 선택하여 반환합니다.
        return random.choice(validProblems)

    def createCaptchaSession(self, keyId: int, captchaProblemId: int, clientToken: str, ipAddress: Optional[str], userAgent: Optional[str]) -> CaptchaSession:
        """
        새로운 캡챠 세션을 생성하고 데이터베이스 세션에 추가합니다.
        이 메소드는 세션에 객체를 추가할 뿐, 커밋(commit)은 직접 수행하지 않습니다.

        Args:
            keyId (int): 이 세션을 요청한 API 키의 ID.
            captchaProblemId (int): 사용자에게 제시된 캡챠 문제의 ID.
            clientToken (str): 이 세션을 식별하는 고유 클라이언트 토큰.
            ipAddress (Optional[str]): 클라이언트의 IP 주소.
            userAgent (Optional[str]): 클라이언트의 User-Agent 정보.

        Returns:
            CaptchaSession: 새로 생성된 CaptchaSession 객체.
        """
        try:
            # 1. 주어진 인자들로 새로운 CaptchaSession 모델 객체를 생성합니다.
            captchaSession = CaptchaSession(
                keyId=keyId,
                captchaProblemId=captchaProblemId,
                clientToken=clientToken,
                ipAddress=ipAddress,
                userAgent=userAgent
            )
            # 2. 생성된 객체를 데이터베이스 세션에 추가합니다.
            self.db.add(captchaSession)
            # 3. 추가된 객체를 반환합니다. (호출한 쪽에서 커밋 필요)
            return captchaSession
        except Exception as e:
            # 4. 세션 추가 중 오류가 발생하면 서버 오류를 발생시킵니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"캡챠 세션 생성 중 오류가 발생했습니다: {e}"
            )

    def getCaptchaSessionByClientToken(self, clientToken: str, for_update: bool = False) -> Optional[CaptchaSession]:
        """
        클라이언트 토큰을 사용하여 캡챠 세션을 조회합니다.
        """
        # 2025-09-08 DEBUG_001: TIMEOUT 로그 중복 방지를 위해 for_update 파라미터를 추가하여 비관적 잠금(Pessimistic Lock)을 적용합니다.
        query = self.db.query(CaptchaSession).filter(
            CaptchaSession.clientToken == clientToken)
        if for_update:
            query = query.with_for_update()
        return query.first()

    def createCaptchaLog(self, session: CaptchaSession, result: CaptchaResult, latency_ms: int, is_correct: Optional[bool], ml_confidence: Optional[float], ml_is_bot: Optional[bool]):
        """
        캡챠 검증 결과를 로그로 기록합니다.
        """
        log_entry = CaptchaLog(
            keyId=session.keyId,
            sessionId=session.id,
            result=result,
            latency_ms=latency_ms,
            is_correct=is_correct,
            ml_confidence=ml_confidence,
            ml_is_bot=ml_is_bot
        )
        self.db.add(log_entry)

    def does_log_exist_for_session(self, session_id: int) -> bool:
        """
        주어진 세션 ID에 대한 로그가 이미 존재하는지 확인합니다.
        """
        return self.db.query(CaptchaLog).filter(CaptchaLog.sessionId == session_id).first() is not None

    def deleteUnloggedSessionsByApiKey(self, apiKeyId: int):
        """
        주어진 API 키에 대해 아직 로그되지 않은 캡챠 세션을 삭제합니다.
        새로운 캡챠 요청이 들어올 때 이전 세션을 정리하여 1:1 트랜잭션을 유지합니다.
        """
        sessionsToDelete = self.db.query(CaptchaSession).filter(
            CaptchaSession.keyId == apiKeyId,
            # 해당 세션에 대한 CaptchaLog 기록이 없는 경우만 선택
            ~self.db.query(CaptchaLog).filter(
                CaptchaLog.sessionId == CaptchaSession.id).exists()
        ).all()
        for session in sessionsToDelete:
            self.db.delete(session)

    def getUnloggedTimedOutSessions(self, timeoutMinutes: int = settings.CAPTCHA_TIMEOUT_MINUTES) -> List[CaptchaSession]:
        """
        아직 로그되지 않았고 타임아웃된 캡챠 세션을 조회합니다.
        """
        timeoutThreshold = datetime.utcnow() - timedelta(minutes=timeoutMinutes)
        return self.db.query(CaptchaSession).filter(
            CaptchaSession.createdAt < timeoutThreshold,
            ~self.db.query(CaptchaLog).filter(
                CaptchaLog.sessionId == CaptchaSession.id).exists()
        ).all()

    def getProblemById(self, problemId: int) -> Optional[CaptchaProblem]:
        """
        문제 ID로 캡챠 문제를 조회합니다.
        """
        return self.db.query(CaptchaProblem).filter(CaptchaProblem.id == problemId).first()