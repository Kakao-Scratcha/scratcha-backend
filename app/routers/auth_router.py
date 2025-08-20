# app/routers/auth_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from app.schemas.token import Token
from app.schemas.user import UserLogin  # UserLogin 스키마 임포트
from app.services.auth_service import (
    AuthService,
    UserNotFoundException,
    InvalidPasswordException,
)  # 서비스 및 예외 임포트

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
    description="사용자 자격 증명(이메일, 비밀번호)을 사용하여 JWT 액세스 토큰을 발급합니다.",
)
async def login_for_access_token(
    formData: UserLogin,  # OAuth2PasswordRequestForm 대신 UserLogin 스키마 사용
    authService: AuthService = Depends(get_auth_service),
):
    try:
        # AuthService를 통해 사용자 인증 시도
        user = authService.authenticateUser(formData.email, formData.password)
    except UserNotFoundException:
        # 사용자를 찾을 수 없을 때의 에러 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="존재하지 않는 사용자입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidPasswordException:
        # 비밀번호가 일치하지 않을 때의 에러 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 로그인 성공 시 토큰 생성 및 반환
    token = authService.createAccessTokenForUser(user)

    return token
