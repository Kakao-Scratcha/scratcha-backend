# backend/models/captcha_problem.py

from sqlalchemy import Column, Integer, String, TEXT, DateTime, func
from sqlalchemy.orm import relationship

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
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="문제 생성 시각"
    )
    expiresAt = Column(
        "expires_at",
        DateTime,
        nullable=False,
        comment="문제 교체 시각 (만료일)"

    )

    # 1:N 관계
    sessions = relationship("CaptchaSession", back_populates="problem")
