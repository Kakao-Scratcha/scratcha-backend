from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Dict, Any, List, Optional
import base64
import re
from datetime import datetime, timedelta
import requests
import uuid

from app.core.config import settings
from app.models.user import User
from app.models.payment import Payment
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    PaymentCreate, PaymentConfirmRequest, PaymentCancelRequest,
    PaymentHistoryResponse, PaymentHistoryItem
)

class PaymentService:
    def __init__(self, db: Session):
        # 1. 데이터베이스 세션 초기화
        self.db = db
        # 2. PaymentRepository 인스턴스 생성
        self.paymentRepo = PaymentRepository(db)
        # 3. 토스 시크릿 키 로드
        self.secretKey = settings.TOSS_SECRET_KEY

    # 1. 암호화된 시크릿 키를 반환하는 헬퍼 함수
    def _getEncryptedSecretKey(self) -> str:
        return "Basic " + base64.b64encode((self.secretKey + ":").encode("utf-8")).decode("utf-8")

    # 1. 사용자 결제 내역을 조회하는 함수
    def getUserPaymentHistory(self, currentUser: User, skip: int, limit: int) -> PaymentHistoryResponse:
        try:
            # 1.1. 현재 사용자의 총 결제 건수 조회
            total = self.paymentRepo.get_payments_count_by_user_id(userId=currentUser.id)
            # 1.2. 현재 사용자의 결제 내역 조회 (페이지네이션 적용)
            payments = self.paymentRepo.get_payments_by_user_id(
                userId=currentUser.id, skip=skip, limit=limit
            )

            # 1.3. 조회된 Payment 모델을 PaymentHistoryItem 스키마로 변환
            historyItems = [
                PaymentHistoryItem(
                    createdAt=p.createdAt,
                    approvedAt=p.approvedAt,
                    orderId=p.orderId,
                    status=p.status,
                    userName=p.user.userName,
                    amount=p.amount,
                    method=p.method,
                    orderName=p.orderName,
                )
                for p in payments
            ]

            # 1.4. PaymentHistoryResponse 객체 생성 및 반환
            return PaymentHistoryResponse(
                userId=currentUser.id,
                total=total,
                page=(skip // limit) + 1,
                size=limit,
                data=historyItems
            )
        except Exception as e:
            # 1.5. 예외 발생 시 500 Internal Server Error 반환
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"결제 내역 조회 중 오류가 발생했습니다: {e}"
            )

    # 1. 결제 상세 정보를 조회하는 함수
    def getPaymentDetails(self, paymentKey: str, currentUser: User) -> Dict[str, Any]:
        # 1.1. 우리 DB에서 결제 기록 조회 및 사용자 권한 확인
        ourPaymentRecord = self.paymentRepo.db.query(Payment).filter(
            Payment.paymentKey == paymentKey,
            Payment.userId == currentUser.id
        ).first()

        # 1.2. 결제 기록이 없거나 권한이 없는 경우 404 Not Found 오류 발생
        if not ourPaymentRecord:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 결제 정보를 찾을 수 없거나 접근 권한이 없습니다."
            )

        # 1.3. 토스페이먼츠 API 인증을 위한 헤더 설정
        headers = {
            "Authorization": self._getEncryptedSecretKey(),
            "Content-Type": "application/json",
        }

        try:
            # 1.4. 토스페이먼츠 API 호출하여 상세 정보 조회
            tossApiUrl = f"https://api.tosspayments.com/v1/payments/{paymentKey}"
            response = requests.get(tossApiUrl, headers=headers)
            # 1.5. HTTP 응답 상태 코드 확인 (2xx가 아니면 예외 발생)
            response.raise_for_status()

            # 1.6. 토스페이먼츠로부터 받은 상세 결제 정보 반환
            return response.json()

        except requests.exceptions.HTTPError as e:
            # 1.7. 토스페이먼츠 API에서 HTTP 에러 발생 시 해당 에러 반환
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"토스페이먼츠 API 조회 중 오류 발생: {e.response.json().get('message', str(e))}"
            )
        except Exception as e:
            # 1.8. 기타 예외 처리 시 500 Internal Server Error 반환
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"결제 정보 조회 중 서버 오류 발생: {str(e)}"
            )

    # 1. 결제를 취소하는 함수
    def cancelPayment(self, paymentKey: str, cancelRequest: PaymentCancelRequest, currentUser: User) -> Dict[str, Any]:
        # 1.1. 우리 DB에서 결제 기록 조회 및 사용자 권한 확인
        ourPaymentRecord = self.paymentRepo.db.query(Payment).filter(
            Payment.paymentKey == paymentKey,
            Payment.userId == currentUser.id
        ).first()

        # 1.2. 결제 기록이 없거나 권한이 없는 경우 404 Not Found 오류 발생
        if not ourPaymentRecord:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 결제 정보를 찾을 수 없거나 접근 권한이 없습니다."
            )

        # 1.3. 토스페이먼츠 API 인증을 위한 헤더 및 멱등키 설정
        headers = {
            "Authorization": self._getEncryptedSecretKey(),
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4())
        }

        # 1.4. 취소 요청 페이로드 구성
        payload = {
            "cancelReason": cancelRequest.cancelReason,
        }
        if cancelRequest.cancelAmount is not None:
            payload["cancelAmount"] = cancelRequest.cancelAmount
        if cancelRequest.refundReceiveAccount is not None:
            payload["refundReceiveAccount"] = cancelRequest.refundReceiveAccount.dict()

        try:
            # 1.5. 토스페이먼츠 API 호출하여 결제 취소 요청
            tossApiUrl = f"https://api.tosspayments.com/v1/payments/{paymentKey}/cancel"
            response = requests.post(tossApiUrl, headers=headers, json=payload)
            # 1.6. HTTP 응답 상태 코드 확인 (2xx가 아니면 예외 발생)
            response.raise_for_status()

            # 1.7. 토스페이먼츠로부터 받은 응답 데이터 파싱
            tossResponseData = response.json()

            # 1.8. 우리 DB 업데이트 (상태 변경 및 잔액 업데이트)
            ourPaymentRecord.status = tossResponseData.get('status')
            ourPaymentRecord.amount = tossResponseData.get('balanceAmount')

            # 1.9. 취소 날짜 기록
            cancelsList = tossResponseData.get('cancels')
            if cancelsList and isinstance(cancelsList, list) and len(cancelsList) > 0:
                lastCancelObj = cancelsList[-1]
                canceledAtStr = lastCancelObj.get('canceledAt')
                if canceledAtStr:
                    ourPaymentRecord.canceledAt = datetime.fromisoformat(
                        canceledAtStr.replace('Z', '+00:00'))

            # 1.10. DB 변경사항 커밋 및 새로고침
            self.paymentRepo.db.add(ourPaymentRecord)
            self.paymentRepo.db.commit()
            self.paymentRepo.db.refresh(ourPaymentRecord)

            # 1.11. 토스페이먼츠로부터 받은 취소 응답 반환
            return tossResponseData

        except requests.exceptions.HTTPError as e:
            # 1.12. 토스페이먼츠 API에서 HTTP 에러 발생 시 해당 에러 반환
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"토스페이먼츠 API 취소 중 오류 발생: {e.response.json().get('message', str(e))}"
            )
        except Exception as e:
            # 1.13. 기타 예외 처리 시 500 Internal Server Error 반환
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"결제 취소 중 서버 오류 발생: {str(e)}"
            )

    # 1. 결제를 승인하고 기록하는 함수
    def confirmPayment(self, data: PaymentConfirmRequest, currentUser: User) -> Dict[str, Any]:
        # 1.1. 토스페이먼츠 API 인증을 위한 헤더 구성
        headers = {
            "Authorization": self._getEncryptedSecretKey(),
            "Content-Type": "application/json",
        }
        # 1.2. 결제 승인 요청 페이로드 구성
        payload = {
            "orderId": data.orderId,
            "amount": data.amount,
            "paymentKey": data.paymentKey,
        }

        try:
            # 1.3. 토스페이먼츠에 결제 승인을 요청
            response = requests.post(
                "https://api.tosspayments.com/v1/payments/confirm",
                headers=headers,
                json=payload
            )
            # 1.4. HTTP 응답 상태 코드 확인 (2xx가 아니면 예외 발생)
            response.raise_for_status()

            # 1.5. 토스페이먼츠로부터 받은 응답 데이터 파싱
            paymentData = response.json()

            # 1.6. API 호출 성공 후, 응답 데이터 유효성 검증 (주문명에서 토큰 수 추출)
            orderName = paymentData.get("orderName")
            match = re.search(r'(\d+)\s*토큰', orderName)
            if not match:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="주문명에서 토큰 수를 추출할 수 없습니다. 'X 토큰 구매' 형식이어야 합니다."
                )
            tokenAmount = int(match.group(1))

            # 1.7. 결제 금액 유효성 검증
            totalAmount = paymentData.get("totalAmount")
            expectedAmount = settings.ALLOWED_PAYMENT_PLANS.get(tokenAmount)
            if expectedAmount is None or totalAmount > expectedAmount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"결제 금액({totalAmount}원)이 정책과 맞지 않습니다."
                )

            try:
                # 1.8. 결제 정보 생성 (세션에 추가, 커밋 X)
                paymentToCreate = PaymentCreate(
                    userId=currentUser.id,
                    orderId=paymentData.get("orderId"),
                    paymentKey=paymentData.get("paymentKey"),
                    status=paymentData.get("status"),
                    method=paymentData.get("method"),
                    orderName=paymentData.get("orderName"),
                    amount=paymentData.get("totalAmount"),
                    currency=paymentData.get("currency"),
                    approvedAt=paymentData.get("approvedAt"),
                )
                dbPayment = self.paymentRepo.create_payment(
                    payment_in=paymentToCreate)

                # 1.9. 사용자 토큰 업데이트 (세션에 추가)
                currentUser.token += tokenAmount
                self.paymentRepo.db.add(currentUser)

                # 1.10. 모든 변경사항을 한 번에 커밋
                self.paymentRepo.db.commit()

                # 1.11. 커밋된 객체들을 리프레시
                self.paymentRepo.db.refresh(currentUser)
                self.paymentRepo.db.refresh(dbPayment)

            except Exception as dbError:
                # 1.12. DB 작업 중 오류 발생 시 롤백 처리
                self.paymentRepo.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"데이터베이스 처리 중 오류가 발생했습니다: {dbError}"
                )

            # 1.13. 성공적으로 처리된 경우, 토스페이먼츠의 응답 반환
            return paymentData

        except requests.exceptions.HTTPError as e:
            # 1.14. 토스페이먼츠 API로부터 HTTP 에러를 받은 경우, 해당 내용을 그대로 클라이언트에 반환
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"토스페이먼츠 결제 승인 중 오류 발생: {e.response.json().get('message', str(e))}"
            )
        except HTTPException as e:
            # 1.15. 유효성 검사 등에서 발생한 HTTP 예외는 그대로 전달
            raise e
        except Exception as e:
            # 1.16. 그 외의 예외가 발생한 경우, 500 에러 반환
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))