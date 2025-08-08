# backend/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .deps_router import get_db
from ..schemas.token import Token
from ..services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

# get_auth_service 의존성


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post(
    "/login",
    response_model=Token,
    summary="로그인",
    description="사용자 자격 증명(이메일, 비밀번호)을 사용하여 JWT 액세스 토큰을 발급합니다."
)
async def login_for_access_token(
    formData: OAuth2PasswordRequestForm = Depends(),  # OAuth2PasswordRequestForm 사용
    authService: AuthService = Depends(get_auth_service)
):
    user = authService.authenticate_user(formData.username, formData.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 로그인 성공 시 토큰 생성 및 반환
    token = authService.create_access_token_for_user(user)

    return token
