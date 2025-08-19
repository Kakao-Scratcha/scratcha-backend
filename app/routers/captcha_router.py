# app/routers/captcha_router.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session


# 프로젝트 의존성 및 모델, 서비스 임포트
from app.core.security import getValidApiKey
from app.models.api_key import ApiKey
from db.session import get_db
from app.schemas.captcha import CaptchaProblemResponse
from app.services.captcha_service import CaptchaService


router = APIRouter(
    prefix="/captcha",
    tags=["captcha"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/problem",
    response_model=CaptchaProblemResponse,
    status_code=status.HTTP_200_OK,
    summary="캡챠 문제 생성",
    description="유효한 API 키로 호출하면 새로운 캡챠 문제와 세션 토큰을 반환합니다."
)
def getCaptchaProblem(
    # 'x-api-key' 헤더를 통해 전달된 유효한 API 키 객체
    apiKey: ApiKey = Depends(getValidApiKey),
    db: Session = Depends(get_db)
):
    service = CaptchaService(db)
    return service.generateCaptchaProblem(apiKey)
