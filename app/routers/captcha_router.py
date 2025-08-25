# app/routers/captcha_router.py

from fastapi import APIRouter, Depends, status, Request, Header
from sqlalchemy.orm import Session
from typing import Annotated

# 프로젝트 의존성 및 모델, 서비스 임포트
from app.core.security import getValidApiKey
from app.models.api_key import ApiKey
from db.session import get_db
from app.schemas.captcha import CaptchaProblemResponse, CaptchaVerificationRequest, CaptchaVerificationResponse
from app.services.captcha_service import CaptchaService


# API 라우터 객체 생성
router = APIRouter(
    prefix="/captcha",
    tags=["Captcha"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/problem",
    response_model=CaptchaProblemResponse,
    status_code=status.HTTP_200_OK,
    summary="새로운 캡챠 문제 요청",
    description="유효한 API 키로 새로운 캡챠 문제(이미지, 선택지 등)와 문제 해결을 위한 고유 토큰을 발급받습니다."
)
def getCaptchaProblem(
    apiKey: ApiKey = Depends(getValidApiKey),
    db: Session = Depends(get_db)
):
    """
    새로운 캡챠 문제를 생성하고 클라이언트에게 반환합니다.

    이 엔드포인트는 'X-Api-Key' 헤더를 통해 유효한 API 키를 받아야만 호출할 수 있습니다.

    Args:
        apiKey (ApiKey): `getValidApiKey` 의존성으로 주입된, 유효성이 검증된 API 키 객체.
        db (Session): `get_db` 의존성으로 주입된 데이터베이스 세션.

    Returns:
        CaptchaProblemResponse: 생성된 캡챠 문제의 상세 정보 (클라이언트 토큰, 이미지 URL, 프롬프트, 선택지).
    """
    captchaService = CaptchaService(db)
    newProblem = captchaService.generateCaptchaProblem(apiKey)
    return newProblem


@router.post(
    "/verify",
    response_model=CaptchaVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="캡챠 답변 검증",
    description="클라이언트로부터 캡챠 문제에 대한 답변을 받아 정답 여부를 검증합니다."
)
def verifyCaptchaAnswer(
    request: CaptchaVerificationRequest,
    fastApiRequest: Request,
    clientToken: Annotated[str, Header(alias="X-Client-Token")],
    db: Session = Depends(get_db)
):
    """
    사용자가 제출한 캡챠 답변의 유효성을 검사합니다.

    Args:
        request (CaptchaVerificationRequest): 클라이언트가 제출한 캡챠 답변 데이터 (정답).
        fastApiRequest (Request): FastAPI의 Request 객체. 클라이언트 IP와 User-Agent를 얻기 위해 사용됩니다.
        clientToken (str): `X-Client-Token` 헤더로 전달되는 고유 클라이언트 토큰.
        db (Session): 데이터베이스 세션.

    Returns:
        CaptchaVerificationResponse: 검증 결과 (성공, 실패, 시간 초과).
    """
    captchaService = CaptchaService(db)
    ipAddress = fastApiRequest.client.host
    userAgent = fastApiRequest.headers.get("user-agent")
    result = captchaService.verifyCaptchaAnswer(
        clientToken, request, ipAddress, userAgent)
    return result
