# app/models/payment.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.config import settings

from db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        comment="결제 고유 식별자 (PK)"
    )
    userId = Column(
        "user_id",
        Integer,
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        comment="결제를 요청한 사용자 ID (FK)"
    )
    paymentKey = Column(
        "payment_key",
        String(255),
        unique=True,
        nullable=False,
        comment="토스페이먼츠의 결제 고유 키"
    )
    orderId = Column(
        "order_id",
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="가맹점에서 관리하는 주문 ID"
    )
    orderName = Column(
        "order_name",
        String(100),
        comment="주문 이름 (예: 토스 티셔츠 외 2건)"
    )
    status = Column(
        "status",
        String(50),
        nullable=False,
        comment="결제 상태 (예: DONE, CANCELED)"
    )
    method = Column(
        "method",
        String(50),
        comment="결제 수단 (예: 카드, 가상계좌)"
    )

    amount = Column(
        "amount",
        Integer,
        nullable=False,
        comment="총 결제 금액"
    )
    currency = Column(
        "currency",
        String(10),
        comment="통화 (예: KRW)"
    )
    approvedAt = Column(
        "approved_at",
        DateTime(timezone=True),
        comment="결제 승인 시간"
    )
    canceledAt = Column(
        "canceled_at",
        DateTime(timezone=True),
        nullable=True,
        comment="결제 취소 시간"
    )
    createdAt = Column(
        "created_at",
        DateTime(timezone=True),
        default=lambda: datetime.now(settings.TIMEZONE),
        nullable=False,
        comment="레코드 생성 시간"
    )

    user = relationship("User", back_populates="payments")