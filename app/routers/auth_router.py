# app/routers/auth_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from app.schemas.token import Token
from app.schemas.user import UserLogin
from app.services.auth_service import (
    AuthService,
    UserNotFoundException,
    InvalidPasswordException,
)

# API 라우터 객체 생성
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)


def getAuthService(db: Session = Depends(get_db)) -> AuthService:
    """
    FastAPI 의존성 주입을 통해 AuthService 인스턴스를 생성하고 반환합니다.

    Args:
        db (Session, optional): `get_db` 의존성에서 제공하는 데이터베이스 세션.

    Returns:
        AuthService: AuthService의 인스턴스.
    """
    return AuthService(db)


@router.post(
    "/login",
    response_model=Token,
    summary="사용자 로그인 및 토큰 발급",
    description="사용자 자격 증명(이메일, 비밀번호)을 검증하고, 성공 시 JWT 액세스 토큰을 발급합니다.",
)
async def loginForAccessToken(
    formData: UserLogin,
    authService: AuthService = Depends(getAuthService),
):
    """
    사용자 로그인을 처리하고 액세스 토큰을 발급합니다.

    Args:
        formData (UserLogin): 사용자가 제출한 이메일과 비밀번호를 포함하는 로그인 데이터.
        authService (AuthService): 의존성으로 주입된 인증 서비스 객체.

    Returns:
        Token: 발급된 JWT 액세스 토큰 정보.
    """
    try:
        # 1. 인증 서비스를 통해 사용자 자격 증명을 검증합니다.
        user = authService.authenticateUser(formData.email, formData.password)
    except UserNotFoundException:
        # 2. 사용자를 찾을 수 없는 경우, 401 Unauthorized 오류를 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="존재하지 않는 사용자입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidPasswordException:
        # 3. 비밀번호가 일치하지 않는 경우, 401 Unauthorized 오류를 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. 인증에 성공하면, 해당 사용자를 위한 액세스 토큰을 생성합니다.
    token = authService.createAccessTokenForUser(user)

    # 5. 생성된 토큰을 클라이언트에게 반환합니다.
    return token