# backend/models/captcha_problem.py

from sqlalchemy import Column, Integer, String, TEXT, DateTime, func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.config import settings

from db.base import Base


class CaptchaProblem(Base):
    __tablename__ = "captcha_problem"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="캡챠 문제 ID"
    )
    imageUrl = Column(
        "image_url",
        TEXT,
        nullable=False,
        comment="S3 이미지 URL"
    )
    originImageUrl = Column(
        "origin_image_url",
        TEXT,
        comment="이미지 원본 URL (적합하지 않은 이미지를 걸러내기 위한 용도)"
    )
    answer = Column(
        "answer",
        String(20),
        nullable=False,
        comment="정답"
    )
    wrongAnswer1 = Column(
        "wrong_answer_1",
        String(20),
        nullable=False,
        comment="오답1"
    )
    wrongAnswer2 = Column(
        "wrong_answer_2",
        String(20),
        nullable=False,
        comment="오답2"
    )
    wrongAnswer3 = Column(
        "wrong_answer_3",
        String(20),
        nullable=False,
        comment="오답3"
    )
    prompt = Column(
        "prompt",
        String(255),
        nullable=False,
        comment="문제 설명"
    )
    difficulty = Column(
        "difficulty",
        Integer,
        nullable=False,
        comment="문제 난이도"
    )
    createdAt = Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(settings.TIMEZONE),
        comment="문제 생성 시각"
    )
    expiresAt = Column(
        "expires_at",
        DateTime(timezone=True),
        nullable=False,
        comment="문제 교체 시각 (만료일)"

    )

    # 1:N 관계
    captchaSession = relationship(
        "CaptchaSession", back_populates="captchaProblem")
