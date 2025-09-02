import base64
import requests
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import getCurrentUser
from app.models.user import User
from db.session import get_db
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentConfirmRequest

# TODO: 개발자센터에 로그인해서 내 결제위젯 연동 키 > 시크릿 키를 입력하세요. 시크릿 키는 외부에 공개되면 안돼요.
# @docs https://docs.tosspayments.com/reference/using-api/api-keys
SECRET_KEY = settings.TOSS_SECRET_KEY

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    responses={404: {"description": "Not found"}},
)


def get_payment_repo(db: Session = Depends(get_db)) -> PaymentRepository:
    """
    FastAPI 의존성 주입을 통해 PaymentRepository 인스턴스를 생성하고 반환합니다.

    Args:
        db (Session, optional): `get_db` 의존성에서 제공하는 데이터베이스 세션.

    Returns:
        PaymentRepository: PaymentRepository의 인스턴스.
    """
    return PaymentRepository(db)


@router.get("/checkout.html", summary="결제 페이지 로드")
def checkout_page():
    return FileResponse("pg/public/checkout.html")


@router.get("/success.html", summary="성공 페이지 로드")
def success_page():
    return FileResponse("pg/public/success.html")


@router.get("/fail.html", summary="실패 페이지 로드")
def fail_page():
    return FileResponse("pg/public/fail.html")


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
    """
    토스페이먼츠 결제를 최종 승인하고 그 결과를 데이터베이스에 저장합니다.

    Args:
        data (PaymentConfirmRequest): 클라이언트에서 받은 결제 승인 정보 (paymentKey, orderId, amount).
        current_user (User): 의존성으로 주입된 현재 로그인된 사용자 객체.
        payment_repo (PaymentRepository): 의존성으로 주입된 결제 리포지토리 객체.

    Returns:
        JSONResponse: 토스페이먼츠로부터 받은 결제 승인 결과 원본.
    """
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
