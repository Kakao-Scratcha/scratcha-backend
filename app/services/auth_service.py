# backend/services/auth_service.py

from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from app.core import security
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.token import Token


# 인증(Authentication) 관련 비즈니스 로직을 처리하는 서비스 클래스입니다.
# 사용자 인증, JWT 토큰 생성 등의 기능을 제공합니다.
class AuthService:

    # 데이터베이스 세션을 주입받아 UserRepository 인스턴스를 초기화합니다.
    def __init__(self, db: Session):
        self.userRepo = UserRepository(db)

    def authenticateUser(self, email: str, password: str) -> Optional[User]:

        # 1. 이메일을 사용하여 데이터베이스에서 사용자를 조회합니다.
        user = self.userRepo.getUserByEmail(email)

        # 2. 사용자 존재 여부 및 비밀번호 일치 여부를 확인합니다.
        #      user가 None이거나 (사용자가 없거나)
        #      security 모듈의 verifyPassword 함수를 통해 평문 비밀번호와
        #      데이터베이스에 저장된 해시된 비밀번호가 일치하지 않으면
        #      인증에 실패한 것으로 간주합니다.
        if not user or not security.verifyPassword(password, user.passwordHash):
            return None

        # 3. 인증에 성공하면 사용자 객체를 반환합니다.
        return user

    # 인증된 사용자에게 JWT 액세스 토큰을 생성하여 반환합니다.
    def createAccessTokenForUser(self, user: User, expires_delta: Optional[timedelta] = None) -> Token:

        # 1. 토큰 만료 시간을 설정합니다.
        #     expires_delta가 제공되면 그 값을 사용하고,
        #     그렇지 않으면 security 모듈에 정의된 기본 만료 시간(분)을 timedelta 객체로 변환하여 사용합니다.
        access_token_expires = expires_delta or timedelta(
            minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)

        # 2. security 모듈의 createAccessToken 함수를 호출하여 JWT를 생성합니다.
        #    - 'sub' (subject) 클레임에 사용자의 이메일을 넣어 토큰의 주체를 식별합니다.
        #    - expires_delta를 전달하여 토큰 만료 시간을 설정합니다.
        access_token = security.createAccessToken(
            data={"sub": user.email}, expires_delta=access_token_expires
        )

        # 3. 생성된 액세스 토큰을 Token Pydantic 스키마 객체로 래핑하여 반환합니다.
        return Token(accessToken=access_token)
