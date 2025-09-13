import base64
import re
from datetime import datetime
import requests
from fastapi import APIRouter, Depends, status, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid

from app.core.config import settings
from app.core.security import getAuthenticatedUser # Updated import
from app.models.user import User
from app.models.payment import Payment
from db.session import get_db
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    PaymentCreate, PaymentConfirmRequest, PaymentCancelRequest,
    PaymentHistoryResponse, PaymentHistoryItem
)
from app.services.payment_service import PaymentService # Import the new service

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    responses={404: {"description": "Not found"}},
)


# @router.get("/checkout.html", summary="결제 페이지 로드")
# def checkout_page():
#     return FileResponse("pg/public/checkout.html")


# @router.get("/success.html", summary="성공 페이지 로드")
# def success_page():
#     return FileResponse("pg/public/success.html")


# @router.get("/fail.html", summary="실패 페이지 로드")
# def fail_page():
#     return FileResponse("pg/public/fail.html")


@router.get("/history", response_model=PaymentHistoryResponse, summary="현재 사용자의 결제 내역 조회")
def getUserPaymentHistory(
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=100, description="가져올 최대 항목 수")
):
    """
    현재 로그인된 사용자의 결제 내역을 최신순으로 조회합니다.
    """
    # 1. PaymentService 인스턴스 생성
    paymentService = PaymentService(db)
    # 2. PaymentService를 통해 사용자 결제 내역 조회
    return paymentService.getUserPaymentHistory(authenticatedUser, skip, limit)


@router.get(
    "/{paymentKey}",
    summary="결제 정보 조회",
    description="paymentKey를 사용하여 토스페이먼츠에서 결제 상세 정보를 조회하고, 우리 DB의 기록과 대조하여 반환합니다.",
    response_model=Dict[str, Any]
)
def getPaymentDetails(
    paymentKey: str,
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
):
    # 1. PaymentService 인스턴스 생성
    paymentService = PaymentService(db)
    # 2. PaymentService를 통해 결제 상세 정보 조회
    return paymentService.getPaymentDetails(paymentKey, authenticatedUser)


@router.post(
    "/{paymentKey}/cancel",
    summary="결제 취소",
    description="paymentKey를 사용하여 승인된 결제를 취소합니다. 부분 취소도 가능합니다.",
    response_model=Dict[str, Any]
)
def cancelPayment(
    paymentKey: str,
    cancelRequest: PaymentCancelRequest,
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
):
    # 1. PaymentService 인스턴스 생성
    paymentService = PaymentService(db)
    # 2. PaymentService를 통해 결제 취소 요청
    return paymentService.cancelPayment(paymentKey, cancelRequest, authenticatedUser)


@router.post(
    "/confirm",
    status_code=status.HTTP_200_OK,
    summary="결제 승인 및 기록",
    description="클라이언트로부터 결제 정보를 받아 토스페이먼츠에 최종 승인 요청을 보내고, 성공 시 우리 데이터베이스에 결제 내역을 기록합니다.",
)
def confirmPayment(
    data: PaymentConfirmRequest,
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
):
    # 1. PaymentService 인스턴스 생성
    paymentService = PaymentService(db)
    # 2. PaymentService를 통해 결제 승인 및 기록
    paymentData = paymentService.confirmPayment(data, authenticatedUser)
    # 3. 승인된 결제 데이터 반환
    return JSONResponse(content=paymentData, status_code=status.HTTP_200_OK)