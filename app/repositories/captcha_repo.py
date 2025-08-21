# app/repositories/captcha_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import random

from app.models.captcha_problem import CaptchaProblem
from app.models.captcha_session import CaptchaSession


class CaptchaRepository:
    def __init__(self, db: Session):
        self.db = db

    def getRandomActiveProblem(self) -> Optional[CaptchaProblem]:
        """활성화된 캡챠 문제 중 하나를 무작위로 선택합니다."""
        validProblems = self.db.query(CaptchaProblem).filter(
            CaptchaProblem.expiresAt > func.now()
        ).all()

        if not validProblems:
            return None

        return random.choice(validProblems)

    def createCaptchaSession(self, keyId: int, captchaProblemId: int, clientToken: str) -> CaptchaSession:
        """새로운 캡챠 세션을 생성합니다. (커밋하지 않음)"""
        captchaSession = CaptchaSession(
            keyId=keyId,
            captchaProblemId=captchaProblemId,
            clientToken=clientToken
        )
        self.db.add(captchaSession)
        return captchaSession
