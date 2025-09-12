# backend/models/captcha_log.py

from sqlalchemy import Column, Enum, Integer, String, TEXT, DateTime, ForeignKey, func, Float, Boolean
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.config import settings


from db.base import Base


class CaptchaResult(enum.Enum):
    SUCCESS = "success"
    FAIL = "fail"
    TIMEOUT = "timeout"


class CaptchaLog(Base):
    __tablename__ = "captcha_log"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="캡챠 로그 ID"
    )
    keyId = Column(
        "api_key_id",
        Integer,
        ForeignKey("api_key.id", ondelete="SET NULL"),
        nullable=True,
        comment="사용된 API 키"
    )
    sessionId = Column(
        "session_id",
        Integer,
        ForeignKey("captcha_session.id", ondelete="CASCADE"),
        nullable=False,
        comment="연결된 캡챠 세션 ID"
    )
    result = Column(
        "result",
        Enum(CaptchaResult),
        nullable=False,
        comment="성공 / 실패 / 타임아웃"
    )
    latency_ms = Column(
        "latency_ms",
        Integer,
        nullable=False,
        comment="캡챠 문제가 해결되기까지 걸린 시간(밀리초)"
    )
    is_correct = Column(
        "is_correct",
        Boolean,
        nullable=True,
        comment="캡챠 문제 정답 여부 (True: 정답, False: 오답)"
    )
    ml_confidence = Column(
        "ml_confidence",
        Float,
        nullable=True,
        comment="머신러닝 모델의 신뢰도 (0.0 ~ 1.0)"
    )
    ml_is_bot = Column(
        "ml_is_bot",
        Boolean,
        nullable=True,
        comment="머신러닝 모델의 봇 판정 (True: 봇, False: 사람)"
    )
    created_at = Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(settings.TIMEZONE),
        comment="문제 생성 시간"
    )

    apiKey = relationship(
        "ApiKey",
        back_populates="captchaLog"
    )

    captchaSession = relationship(
        "CaptchaSession",
        back_populates="captchaLog"
    )