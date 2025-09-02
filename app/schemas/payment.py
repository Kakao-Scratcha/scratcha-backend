# app/schemas/payment.py
from pydantic import BaseModel
from typing import Optional
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
        orm_mode = True


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
