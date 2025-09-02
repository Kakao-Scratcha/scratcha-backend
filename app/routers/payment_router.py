import base64
import requests
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from app.core.config import settings

# TODO: 개발자센터에 로그인해서 내 결제위젯 연동 키 > 시크릿 키를 입력하세요. 시크릿 키는 외부에 공개되면 안돼요.
# @docs https://docs.tosspayments.com/reference/using-api/api-keys
SECRET_KEY = settings.TOSS_SECRET_KEY

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    responses={404: {"description": "Not found"}},
)


class PaymentConfirmRequest(BaseModel):
    paymentKey: str
    orderId: str
    amount: int


@router.post(
    "/confirm",
    status_code=status.HTTP_200_OK,
    summary="결제 검증 요청",
    description="successUrl에서 호출합니다. paymetKey, orderId, amout를 필수로 전달받아 우리의 서버에서 토스 페이먼츠 검증 API 를 호출하여 결제내역을 검증합니다."
)
async def confirmPayment(request: Request, data: PaymentConfirmRequest):
    # 토스페이먼츠 API는 시크릿 키를 사용자 ID로 사용하고, 비밀번호는 사용하지 않습니다.
    # 비밀번호가 없다는 것을 알리기 위해 시크릿 키 뒤에 콜론을 추가합니다.
    # @docs https://docs.tosspayments.com/reference/using-api/authorization#%EC%9D%B8%EC%A6%9D
    encryptedSecretKey = "Basic " + \
        base64.b64encode((SECRET_KEY + ":").encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": encryptedSecretKey,
        "Content-Type": "application/json",
    }

    payload = {
        "orderId": data.orderId,
        "amount": data.amount,
        "paymentKey": data.paymentKey,
    }

    try:
        response = requests.post(
            "https://api.tosspayments.com/v1/payments/confirm",
            headers=headers,
            json=payload
        )
        response.raise_for_status()  # 응답 코드가 2xx가 아니면 예외 발생

        # TODO: 결제 완료 비즈니스 로직을 구현, order 테이블을 생성해서 기록.
        return JSONResponse(content=response.json(), status_code=response.status_code)

    except requests.exceptions.HTTPError as e:
        # TODO: 결제 실패 비즈니스 로직을 구현하세요.
        return JSONResponse(content=e.response.json(), status_code=e.response.status_code)
    except Exception as e:
        # 기타 예외 처리
        return JSONResponse(content={"message": str(e), "code": "UNKNOWN_ERROR"}, status_code=500)
