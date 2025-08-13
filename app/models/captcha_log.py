# backend/models/captcha_log.py

from sqlalchemy import Column, Enum, Integer, String, TEXT, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
import enum


from db.base import Base


class CaptchaResult(enum.Enum):
    SUCCESS = "success"
    FAIL = "fail"


class CaptchaLog(Base):
    __tablename__ = "captcha_log"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="캡챠 로그 ID"
    )
    apiKeyId = Column(
        "api_key_id",
        Integer,
        ForeignKey("api_key.id"),
        nullable=False,
        comment="사용된 API 키"
    )
    sessionId = Column(
        "session_id",
        Integer,
        ForeignKey("captcha_session.id", ondelete="CASCADE"),
        nullable=False,
        comment="연결된 캡챠 세션 ID"
    )
    ipAddress = Column(
        "ip_address",
        String(45),
        comment="요청자 IP"
    )
    userAgent = Column(
        "user_agent",
        TEXT,
        comment="요청자 브라우저 정보"
    )
    result = Column(
        "result",
        Enum(CaptchaResult),
        nullable=False,
        comment="성공 / 실패 결과"
    )
    latency_ms = Column(
        "latency_ms",
        Integer,
        nullable=False,
        comment="응답 지연 시간 (ms)"
    )
    createdAt = Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="생성 시각"
    )

    # N:1 관계
    session = relationship("CaptchaSession", back_populates="logs")
