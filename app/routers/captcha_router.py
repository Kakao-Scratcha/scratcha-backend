# app/routers/captcha_router.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session


# 프로젝트 의존성 및 모델, 서비스 임포트
from app.core.security import getValidApiKey
from app.models.api_key import ApiKey
from db.session import get_db
from app.schemas.captcha import CaptchaProblemResponse
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

    이 엔드포인트는 'x-api-key' 헤더를 통해 유효한 API 키를 받아야만 호출할 수 있습니다.

    Args:
        apiKey (ApiKey): `getValidApiKey` 의존성으로 주입된, 유효성이 검증된 API 키 객체.
        db (Session): `get_db` 의존성으로 주입된 데이터베이스 세션.

    Returns:
        CaptchaProblemResponse: 생성된 캡챠 문제의 상세 정보 (클라이언트 토큰, 이미지 URL, 프롬프트, 선택지).
    """
    # 1. CaptchaService 인스턴스를 생성합니다.
    captchaService = CaptchaService(db)
    # 2. 캡챠 서비스의 문제 생성 로직을 호출합니다.
    # 이 때, 어떤 API 키가 문제를 요청했는지 식별하기 위해 apiKey 객체를 전달합니다.
    newProblem = captchaService.generateCaptchaProblem(apiKey)
    # 3. 생성된 캡챠 문제 정보를 클라이언트에게 반환합니다.
    return newProblem