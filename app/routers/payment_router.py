import base64
from datetime import datetime
import requests
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid

from app.core.config import settings
from app.core.security import getCurrentUser
from app.models.user import User
from app.models.payment import Payment
from db.session import get_db
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentConfirmRequest, PaymentCancelRequest

# TODO: 개발자센터에 로그인해서 내 결제위젯 연동 키 > 시크릿 키를 입력하세요.
# @docs https://docs.tosspayments.com/reference/using-api/api-keys
SECRET_KEY = settings.TOSS_SECRET_KEY

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    responses={404: {"description": "Not found"}},
)


def get_payment_repo(db: Session = Depends(get_db)) -> PaymentRepository:
    """
    FastAPI 의존성 주입을 통해 PaymentRepository 인스턴스를 생성하고 반환합니다.
    """
    return PaymentRepository(db)


# @router.get("/checkout.html", summary="결제 페이지 로드")
# def checkout_page():
#     return FileResponse("pg/public/checkout.html")


# @router.get("/success.html", summary="성공 페이지 로드")
# def success_page():
#     return FileResponse("pg/public/success.html")


# @router.get("/fail.html", summary="실패 페이지 로드")
# def fail_page():
#     return FileResponse("pg/public/fail.html")


@router.get(
    "/{paymentKey}",
    summary="결제 정보 조회",
    description="paymentKey를 사용하여 토스페이먼츠에서 결제 상세 정보를 조회하고, 우리 DB의 기록과 대조하여 반환합니다.",
    response_model=Dict[str, Any]
)
def getPaymentDetails(
    paymentKey: str,
    current_user: User = Depends(getCurrentUser),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
):
    # 1. 우리 DB에서 결제 기록 조회 및 사용자 권한 확인
    our_payment_record = payment_repo.db.query(Payment).filter(
        Payment.paymentKey == paymentKey,
        Payment.userId == current_user.id
    ).first()

    if not our_payment_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 결제 정보를 찾을 수 없거나 접근 권한이 없습니다."
        )

    # 2. 토스페이먼츠 API 인증을 위한 시크릿 키 준비
    encrypted_secret_key = "Basic " + \
        base64.b64encode((SECRET_KEY + ":").encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": encrypted_secret_key,
        "Content-Type": "application/json",
    }

    try:
        # 3. 토스페이먼츠 API 호출하여 상세 정보 조회
        toss_api_url = f"https://api.tosspayments.com/v1/payments/{paymentKey}"
        response = requests.get(toss_api_url, headers=headers)
        response.raise_for_status()  # 2xx가 아니면 예외 발생

        # 4. 토스페이먼츠로부터 받은 상세 결제 정보 반환
        return response.json()

    except requests.exceptions.HTTPError as e:
        # 토스페이먼츠 API에서 에러 발생 시 해당 에러 반환
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"토스페이먼츠 API 조회 중 오류 발생: {e.response.json().get('message', str(e))}"
        )
    except Exception as e:
        # 기타 예외 처리
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"결제 정보 조회 중 서버 오류 발생: {str(e)}"
        )


@router.post(
    "/{paymentKey}/cancel",
    summary="결제 취소",
    description="paymentKey를 사용하여 승인된 결제를 취소합니다. 부분 취소도 가능합니다.",
    response_model=Dict[str, Any]
)
def cancelPayment(
    paymentKey: str,
    cancel_request: PaymentCancelRequest,
    current_user: User = Depends(getCurrentUser),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
):
    # 1. 우리 DB에서 결제 기록 조회 및 사용자 권한 확인
    our_payment_record = payment_repo.db.query(Payment).filter(
        Payment.paymentKey == paymentKey,
        Payment.userId == current_user.id
    ).first()

    if not our_payment_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 결제 정보를 찾을 수 없거나 접근 권한이 없습니다."
        )

    # 2. 토스페이먼츠 API 인증을 위한 시크릿 키 준비
    encrypted_secret_key = "Basic " + \
        base64.b64encode((SECRET_KEY + ":").encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": encrypted_secret_key,
        "Content-Type": "application/json",
        "Idempotency-Key": str(uuid.uuid4())  # 멱등키 추가
    }

    payload = {
        "cancelReason": cancel_request.cancelReason,
    }
    if cancel_request.cancelAmount is not None:
        payload["cancelAmount"] = cancel_request.cancelAmount
    if cancel_request.refundReceiveAccount is not None:
        payload["refundReceiveAccount"] = cancel_request.refundReceiveAccount.dict()

    try:
        # 3. 토스페이먼츠 API 호출하여 결제 취소 요청
        toss_api_url = f"https://api.tosspayments.com/v1/payments/{paymentKey}/cancel"
        response = requests.post(toss_api_url, headers=headers, json=payload)
        response.raise_for_status()  # 2xx가 아니면 예외 발생

        toss_response_data = response.json()  # 응답 데이터를 먼저 할당

        # 4. 우리 DB 업데이트 (상태 변경)
        # Payment 객체의 status 필드를 참고하여 CANCELED 또는 PARTIAL_CANCELED로 변경
        our_payment_record.status = toss_response_data.get('status')
        # 부분 취소의 경우 amount를 balanceAmount로 업데이트
        # balanceAmount는 취소 후 남은 금액을 의미합니다.
        our_payment_record.amount = toss_response_data.get('balanceAmount')

        # 취소 날짜 기록 (cancels 배열의 마지막 객체에서 canceledAt 추출)
        cancels_list = toss_response_data.get('cancels')
        if cancels_list and isinstance(cancels_list, list) and len(cancels_list) > 0:
            last_cancel_obj = cancels_list[-1]
            canceled_at_str = last_cancel_obj.get('canceledAt')
            if canceled_at_str:
                # ISO 8601 문자열을 datetime 객체로 변환
                our_payment_record.canceledAt = datetime.fromisoformat(
                    canceled_at_str.replace('Z', '+00:00'))

        payment_repo.db.add(our_payment_record)
        payment_repo.db.commit()
        payment_repo.db.refresh(our_payment_record)

        # 5. 토스페이먼츠로부터 받은 취소 응답 반환
        return toss_response_data

    except requests.exceptions.HTTPError as e:
        # 토스페이먼츠 API에서 에러 발생 시 해당 에러 반환
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"토스페이먼츠 API 취소 중 오류 발생: {e.response.json().get('message', str(e))}"
        )
    except Exception as e:
        # 기타 예외 처리
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"결제 취소 중 서버 오류 발생: {str(e)}"
        )


@router.post(
    "/confirm",
    status_code=status.HTTP_200_OK,
    summary="결제 승인 및 기록",
    description="클라이언트로부터 결제 정보를 받아 토스페이먼츠에 최종 승인 요청을 보내고, 성공 시 우리 데이터베이스에 결제 내역을 기록합니다.",
)
def confirmPayment(
    data: PaymentConfirmRequest,
    current_user: User = Depends(getCurrentUser),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
):
    # 1. 토스페이먼츠 API 인증을 위한 시크릿 키를 준비합니다.
    #    - 시크릿 키 뒤에 콜론을 붙여 Base64로 인코딩하는 Basic 인증 방식을 사용합니다.
    encrypted_secret_key = "Basic " + \
        base64.b64encode((SECRET_KEY + ":").encode("utf-8")).decode("utf-8")

    # 2. 토스페이먼츠 결제 승인 API에 보낼 헤더와 페이로드를 구성합니다.
    headers = {
        "Authorization": encrypted_secret_key,
        "Content-Type": "application/json",
    }
    payload = {
        "orderId": data.orderId,
        "amount": data.amount,
        "paymentKey": data.paymentKey,
    }

    try:
        # 3. 토스페이먼츠에 결제 승인을 요청합니다.
        response = requests.post(
            "https://api.tosspayments.com/v1/payments/confirm",
            headers=headers,
            json=payload
        )
        response.raise_for_status()  # 응답 코드가 2xx가 아니면 예외를 발생시킵니다.

        # 4. API 호출 성공 시, 응답받은 JSON 데이터를 변수에 저장합니다.
        payment_data = response.json()

        # 5. 우리 데이터베이스에 저장할 결제 정보 스키마를 생성합니다.
        payment_to_create = PaymentCreate(
            userId=current_user.id,  # JWT 토큰에서 얻은 사용자 ID
            orderId=payment_data.get("orderId"),
            paymentKey=payment_data.get("paymentKey"),
            status=payment_data.get("status"),
            method=payment_data.get("method"),
            orderName=payment_data.get("orderName"),
            amount=payment_data.get("totalAmount"),
            currency=payment_data.get("currency"),
            approvedAt=payment_data.get("approvedAt"),
        )

        # 6. 리포지토리를 통해 데이터베이스에 결제 정보를 기록합니다.
        payment_repo.create_payment(payment_in=payment_to_create)

        # 7. 성공적으로 처리된 경우, 토스페이먼츠의 응답을 그대로 클라이언트에 반환합니다.
        return JSONResponse(content=payment_data, status_code=response.status_code)

    except requests.exceptions.HTTPError as e:
        # 8. 토스페이먼츠 API로부터 HTTP 에러를 받은 경우, 해당 내용을 그대로 클라이언트에 반환합니다.
        return JSONResponse(content=e.response.json(), status_code=e.response.status_code)
    except Exception as e:
        # 9. 그 외의 예외가 발생한 경우, 상세 트레이스백을 출력하고 500 에러를 반환합니다.
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
