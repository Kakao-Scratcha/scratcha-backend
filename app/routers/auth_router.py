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
    UserSoftDeletedException,
)

# API 라우터 객체 생성
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/login",
    response_model=Token,
    summary="사용자 로그인 및 토큰 발급",
    description="사용자 자격 증명(이메일, 비밀번호)을 검증하고, 성공 시 JWT 액세스 토큰을 발급합니다.",
)
async def loginForAccessToken(
    formData: UserLogin,
    db: Session = Depends(get_db),  # Direct DB session injection
):
    """
    사용자 로그인을 처리하고 액세스 토큰을 발급합니다.

    Args:
        formData (UserLogin): 사용자가 제출한 이메일과 비밀번호를 포함하는 로그인 데이터.
        authService (AuthService): 의존성으로 주입된 인증 서비스 객체.

    Returns:
        Token: 발급된 JWT 액세스 토큰 정보.
    """
    # 1. AuthService 인스턴스 생성
    authService = AuthService(db)
    try:
        # 2. 인증 서비스를 통해 사용자 자격 증명을 검증합니다.
        user = authService.authenticateUser(formData.email, formData.password)
    except UserNotFoundException:
        # 3. 사용자를 찾을 수 없는 경우, 401 Unauthorized 오류를 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="존재하지 않는 사용자입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidPasswordException:
        # 4. 비밀번호가 일치하지 않는 경우, 401 Unauthorized 오류를 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except UserSoftDeletedException:
        # 5. 사용자가 소프트 삭제된 경우, 403 Forbidden 오류를 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="삭제된 계정입니다. 문의 페이지를 통해 문의해주세요.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. 인증에 성공하면, 해당 사용자를 위한 액세스 토큰을 생성합니다.
    token = authService.createAccessTokenForUser(user)

    # 6. 생성된 토큰을 클라이언트에게 반환합니다.
    return token
