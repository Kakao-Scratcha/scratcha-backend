# backend/models/captcha_session.py


from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from db.base import Base


class CaptchaSession(Base):
    __tablename__ = "captcha_session"

    id = Column(
        Integer,
        primary_key=True,
        comment="캡챠 세션 ID"
    )

    keyId = Column(
        "api_key_id",
        Integer,
        ForeignKey("api_key.id"),
        nullable=False,
        comment="사용된 API 키"
    )

    captchaProblemId = Column(
        "captcha_problem_id",
        Integer,
        ForeignKey("captcha_problem.id", ondelete="CASCADE"),
        nullable=False,
        comment="랜덤으로 가져온 문제 ID"
    )
    clientToken = Column(
        "client_token",
        String(100),
        unique=True,
        nullable=False,
        comment="클라이언트에 전달할 고유 토큰 (1회용)"
    )

    createdAt = Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="생성 시각"
    )

    # N:1 관계
    captchaProblem = relationship(
        "CaptchaProblem", back_populates="captchaSession")

    # 1:N 관계
    captchaLog = relationship("CaptchaLog", back_populates="captchaSession")
