# app/schemas/payment.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PaymentBase(BaseModel):
    """결제 정보의 기본 필드를 정의하는 스키마"""
    orderId: str = Field(..., description="주문 ID", example="order-123")
    paymentKey: str = Field(..., description="결제 키", example="paykey-456")
    status: str = Field(..., description="결제 상태", example="DONE")
    method: Optional[str] = Field(None, description="결제 수단", example="카드")
    orderName: Optional[str] = Field(None, description="주문 이름", example="캡챠 서비스 이용권")
    amount: int = Field(..., description="결제 금액", example=10000)
    currency: Optional[str] = Field(None, description="통화", example="KRW")
    approvedAt: Optional[datetime] = Field(None, description="승인 일시", example="2024-01-01T12:00:00")
    canceledAt: Optional[datetime] = Field(None, description="취소 일시", example=None)


class PaymentCreate(PaymentBase):
    """새로운 결제 정보를 생성할 때 사용하는 스키마"""
    userId: int = Field(..., description="사용자 ID", example=1)


class Payment(PaymentBase):
    """API 응답으로 사용될 결제 정보 스키마"""
    id: int = Field(..., description="결제 ID", example=1)
    userId: int = Field(..., description="사용자 ID", example=1)
    createdAt: datetime = Field(..., description="생성 일시", example="2024-01-01T12:00:00")

    class Config:
        from_attributes = True


class PaymentHistoryItem(BaseModel):
    """결제 내역의 개별 항목을 정의하는 스키마"""
    createdAt: datetime = Field(..., description="주문일시")
    approvedAt: Optional[datetime] = Field(None, description="결제일시")
    orderId: str = Field(..., description="주문번호")
    status: str = Field(..., description="결제상태")
    userName: str = Field(..., description="구매자명")
    amount: int = Field(..., description="결제액")
    method: Optional[str] = Field(None, description="결제수단")
    orderName: Optional[str] = Field(None, description="구매상품")

    class Config:
        from_attributes = True


class PaymentHistoryResponse(BaseModel):
    """결제 내역 조회 API 응답을 위한 스키마"""
    userId: int = Field(..., description="사용자 ID")
    data: List[PaymentHistoryItem] = Field(..., description="결제 내역 데이터 배열")
    total: int = Field(..., description="전체 결제 내역 수")
    page: int = Field(..., description="현재 페이지 번호")
    size: int = Field(..., description="페이지 당 항목 수")


class PaymentConfirmRequest(BaseModel):
    """결제 승인 요청 시 클라이언트로부터 받는 데이터 모델"""
    paymentKey: str = Field(..., description="결제 키", example="paykey-789")
    orderId: str = Field(..., description="주문 ID", example="order-456")
    amount: int = Field(..., description="결제 금액", example=10000)


class RefundReceiveAccount(BaseModel):
    """결제 취소 후 환불받을 계좌 정보 스키마"""
    bank: str = Field(..., description="은행 이름", example="국민은행")
    accountNumber: str = Field(..., description="계좌 번호", example="1234567890")
    holderName: str = Field(..., description="예금주", example="홍길동")


class PaymentCancelRequest(BaseModel):
    """결제 취소 요청 시 클라이언트로부터 받는 데이터 모델"""
    cancelReason: str = Field(..., description="취소 사유", example="단순 변심")
    cancelAmount: Optional[int] = Field(None, description="취소 금액", example=5000)
    refundReceiveAccount: Optional[RefundReceiveAccount] = Field(None, description="환불 계좌 정보")


class PaymentWebhookPayload(BaseModel):
    """토스페이먼츠 웹훅 이벤트 페이로드 스키마"""
    eventType: str = Field(..., description="이벤트 타입", example="PAYMENT_SUCCESS")
    data: dict = Field(..., description="이벤트 데이터", example={
        "mId": "test_m_id",
        "version": "1.3",
        "paymentKey": "test_payment_key",
        "orderId": "test_order_id",
        "orderName": "test_order_name",
        "status": "DONE",
        "requestedAt": "2024-01-01T12:00:00+09:00",
        "approvedAt": "2024-01-01T12:00:00+09:00",
        "totalAmount": 10000,
        "method": "카드"
    })
