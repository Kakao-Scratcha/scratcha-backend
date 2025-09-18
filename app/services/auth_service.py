# backend/services/auth_service.py

from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
from fastapi import HTTPException, status

from app.core import security
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.token import Token

# Custom Exceptions
class UserNotFoundException(Exception):
    """사용자를 찾을 수 없을 때 발생하는 예외입니다."""
    pass

class InvalidPasswordException(Exception):
    """비밀번호가 일치하지 않을 때 발생하는 예외입니다."""
    pass

class UserSoftDeletedException(Exception):
    """소프트 삭제된 사용자가 로그인 시도할 때 발생하는 예외입니다."""
    pass

# 인증(Authentication) 관련 비즈니스 로직을 처리하는 서비스 클래스입니다.
# 사용자 인증, JWT 토큰 생성 등의 기능을 제공합니다.
class AuthService:

    def __init__(self, db: Session):
        """
        AuthService의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        # 데이터베이스 세션을 주입받아 UserRepository 인스턴스를 초기화합니다.
        self.userRepo = UserRepository(db)

    def authenticateUser(self, email: str, password: str) -> User:
        """
        사용자 자격 증명(이메일, 비밀번호)을 검증하고, 인증된 사용자 객체를 반환합니다.

        Args:
            email (str): 사용자의 이메일 주소.
            password (str): 사용자가 입력한 비밀번호.

        Returns:
            User: 인증에 성공한 사용자 객체.
        """
        try:
            # 1. 이메일을 사용하여 데이터베이스에서 사용자를 조회합니다.
            user = self.userRepo.getUserByEmail(email, includeDeleted=True)
        except Exception as e:
            # 2. 사용자 조회 중 데이터베이스 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용자 인증 중 오류가 발생했습니다: {e}"
            )

        # 3. 사용자 존재 여부를 확인합니다.
        if not user:
            raise UserNotFoundException()

        # 4. 비밀번호 일치 여부를 확인합니다.
        if not security.verifyPassword(password, user.passwordHash):
            raise InvalidPasswordException()

        # 5. 인증에 성공하면 사용자 객체를 반환합니다.
        # 6. 사용자가 소프트 삭제되었는지 확인합니다.
        if user.deletedAt is not None:
            raise UserSoftDeletedException()

        return user

    def createAccessTokenForUser(self, user: User, expiresDelta: Optional[timedelta] = None) -> Token:
        """
        인증된 사용자에게 JWT 액세스 토큰을 생성하여 반환합니다.

        Args:
            user (User): 토큰을 생성할 사용자 객체.
            expiresDelta (Optional[timedelta], optional): 토큰의 만료 시간 델타. None일 경우 기본값 사용. Defaults to None.

        Returns:
            Token: 생성된 JWT 액세스 토큰 정보를 담은 Token 스키마 객체.
        """
        try:
            # 1. 토큰 만료 시간을 설정합니다.
            # expiresDelta가 제공되면 그 값을 사용하고, 그렇지 않으면 security 모듈에 정의된 기본 만료 시간(분)을 timedelta 객체로 변환하여 사용합니다.
            accessTokenExpires = expiresDelta or timedelta(
                minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)

            # 2. security 모듈의 createAccessToken 함수를 호출하여 JWT를 생성합니다.
            #    - 'sub' (subject) 클레임에 사용자의 이메일을 넣어 토큰의 주체를 식별합니다.
            #    - expiresDelta를 전달하여 토큰 만료 시간을 설정합니다.
            accessToken = security.createAccessToken(
                data={"sub": user.email}, expires_delta=accessTokenExpires
            )

            # 3. 생성된 액세스 토큰을 Token Pydantic 스키마 객체로 래핑하여 반환합니다.
            return Token(accessToken=accessToken)
        except Exception as e:
            # 4. 토큰 생성 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"액세스 토큰 생성 중 오류가 발생했습니다: {e}"
            )
