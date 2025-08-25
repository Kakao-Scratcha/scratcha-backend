# app/repositories/captcha_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import random
from fastapi import HTTPException, status

from app.models.captcha_problem import CaptchaProblem
from app.models.captcha_session import CaptchaSession
from app.models.captcha_log import CaptchaLog, CaptchaResult


class CaptchaRepository:
    def __init__(self, db: Session):
        """
        CaptchaRepository의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db

    def getRandomActiveProblem(self) -> Optional[CaptchaProblem]:
        """
        데이터베이스에서 활성화된 (만료되지 않은) 캡챠 문제 중 하나를 무작위로 선택하여 반환합니다.

        Returns:
            Optional[CaptchaProblem]: 무작위로 선택된 활성 CaptchaProblem 객체. 활성 문제가 없으면 None을 반환합니다.
        """
        try:
            # 1. 현재 시간을 기준으로 아직 만료되지 않은 모든 캡챠 문제를 데이터베이스에서 조회합니다.
            validProblems = self.db.query(CaptchaProblem).filter(
                CaptchaProblem.expiresAt > func.now()
            ).all()
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

    def createCaptchaSession(self, keyId: int, captchaProblemId: int, clientToken: str) -> CaptchaSession:
        """
        새로운 캡챠 세션을 생성하고 데이터베이스 세션에 추가합니다.
        이 메소드는 세션에 객체를 추가할 뿐, 커밋(commit)은 직접 수행하지 않습니다.

        Args:
            keyId (int): 이 세션을 요청한 API 키의 ID.
            captchaProblemId (int): 사용자에게 제시된 캡챠 문제의 ID.
            clientToken (str): 이 세션을 식별하는 고유 클라이언트 토큰.

        Returns:
            CaptchaSession: 새로 생성된 CaptchaSession 객체.
        """
        try:
            # 1. 주어진 인자들로 새로운 CaptchaSession 모델 객체를 생성합니다.
            captchaSession = CaptchaSession(
                keyId=keyId,
                captchaProblemId=captchaProblemId,
                clientToken=clientToken
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

    def getCaptchaSessionByClientToken(self, clientToken: str) -> Optional[CaptchaSession]:
        """
        클라이언트 토큰을 사용하여 캡챠 세션을 조회합니다.

        Args:
            clientToken (str): 조회할 캡챠 세션의 클라이언트 토큰.

        Returns:
            Optional[CaptchaSession]: 조회된 캡챠 세션 객체. 세션이 없으면 None을 반환합니다.
        """
        return self.db.query(CaptchaSession).filter(CaptchaSession.clientToken == clientToken).first()

    def createCaptchaLog(self, session: CaptchaSession, result: CaptchaResult, latency_ms: int, ipAddress: Optional[str], userAgent: Optional[str]):
        """
        캡챠 검증 결과를 로그로 기록합니다.

        Args:
            session (CaptchaSession): 검증이 완료된 캡챠 세션.
            result (CaptchaResult): 검증 결과 (성공, 실패, 타임아웃).
            latency_ms (int): 응답 시간 (밀리초).
            ipAddress (Optional[str]): 클라이언트의 IP 주소.
            userAgent (Optional[str]): 클라이언트의 User-Agent 정보.
        """
        log_entry = CaptchaLog(
            keyId=session.keyId,
            sessionId=session.id,
            ipAddress=ipAddress,
            userAgent=userAgent,
            result=result,
            latency_ms=latency_ms
        )
        self.db.add(log_entry)

    def logExistForSession(self, session_id: int) -> bool:
        """
        주어진 세션 ID에 대한 로그가 이미 존재하는지 확인합니다.

        Args:
            session_id (int): 확인할 캡챠 세션의 ID.

        Returns:
            bool: 로그가 존재하면 True, 그렇지 않으면 False.
        """
        return self.db.query(CaptchaLog).filter(CaptchaLog.sessionId == session_id).first() is not None
