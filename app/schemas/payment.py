# app/schemas/payment.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PaymentBase(BaseModel):
    """결제 정보의 기본 필드를 정의하는 스키마"""
    orderId: str
    paymentKey: str
    status: str
    method: Optional[str] = None
    orderName: Optional[str] = None
    amount: int
    currency: Optional[str] = None
    approvedAt: Optional[datetime] = None
    canceledAt: Optional[datetime] = None


class PaymentCreate(PaymentBase):
    """새로운 결제 정보를 생성할 때 사용하는 스키마"""
    userId: int


class Payment(PaymentBase):
    """API 응답으로 사용될 결제 정보 스키마"""
    id: int
    userId: int
    createdAt: datetime

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
    paymentKey: str
    orderId: str
    amount: int


class RefundReceiveAccount(BaseModel):
    """결제 취소 후 환불받을 계좌 정보 스키마"""
    bank: str
    accountNumber: str
    holderName: str


class PaymentCancelRequest(BaseModel):
    """결제 취소 요청 시 클라이언트로부터 받는 데이터 모델"""
    cancelReason: str
    cancelAmount: Optional[int] = None
    refundReceiveAccount: Optional[RefundReceiveAccount] = None


class PaymentWebhookPayload(BaseModel):
    """토스페이먼츠 웹훅 이벤트 페이로드 스키마"""
    eventType: str
    data: dict
