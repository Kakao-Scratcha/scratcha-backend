# backend/models/usage_stats.py

from sqlalchemy import Column, Date, Integer, String, TEXT, DateTime, ForeignKey, func, Float
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.config import settings


from db.base import Base


class UsageStats(Base):
    __tablename__ = "usage_stats"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="사용량 통계 ID"
    )
    keyId = Column(
        "api_key_id",
        Integer,
        ForeignKey("api_key.id", ondelete="SET NULL"),
        nullable=True,
        comment="통계의 기준이되는 API 키"
    )
    date = Column(
        "date",
        Date,
        nullable=False,
        comment="통계 기준 날짜 (예: 2025-07-01)"
    )
    captchaTotalRequests = Column(
        "captcha_total_requests",
        Integer,
        nullable=False,
        default=0,
        comment="전체 요청 수"
    )
    captchaSuccessCount = Column(
        "captcha_success_count",
        Integer,
        nullable=False,
        default=0,
        comment="성공 응답 수"
    )
    captchaFailCount = Column(
        "captcha_fail_count",
        Integer,
        nullable=False,
        default=0,
        comment="실패 응답 수"
    )
    captchaTimeoutCount = Column(
        "captcha_timeout_count",
        Integer,
        nullable=False,
        default=0,
        comment="타임아웃 응답 수"
    )
    totalLatencyMs = Column(
        "total_latency_ms",
        Integer,
        nullable=False,
        default=0,
        comment="총 지연 시간 (ms)"
    )
    verificationCount = Column(
        "verification_count",
        Integer,
        nullable=False,
        default=0,
        comment="총 검증 횟수"
    )
    avgResponseTimeMs = Column(
        "avg_response_time_ms",
        Float,
        nullable=False,
        default=0.0,
        comment="평균 응답 시간 (ms)"
    )
    created_at = Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(settings.TIMEZONE),
        comment="레코드 생성 시각 (기본값으로 현재 시각 사용)"
    )

    # 관계 설정 (API 키 객체를 역방향으로 참조)
    apiKey = relationship("ApiKey", back_populates="usageStats")
