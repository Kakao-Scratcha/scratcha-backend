# backend/dashboard_api/app/core/security.py

from dashboard_api.app.repositories.user_repo import UserRepository
from dashboard_api.app.models.user import User, UserRole
from db.session import SessionLocal
from dashboard_api.app.routers.deps import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from dotenv import load_dotenv
import os

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv(
    "SECRET_KEY", "fallback-super-secret-key")  # 환경 변수 사용 권장
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2PasswordBearer는 로그인 엔드포인트(/auth/token)에서 사용되어
# Swagger UI의 "Authorize" 팝업에 'password' flow를 제공합니다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/dashboard/auth/login")

# HTTPBearer는 보호된 엔드포인트에서 클라이언트가 보낸 JWT 토큰을 추출하는 데 사용됩니다.
# Swagger UI에는 단순한 'Bearer' 토큰 입력 필드를 제공합니다.
http_bearer_scheme = HTTPBearer()  # tokenUrl을 지정하지 않습니다.


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# get_current_user_email 함수를 수정하여 HTTPBearer 스키마를 사용하도록 합니다.
# token_object는 HTTPBearer 객체이며, 실제 토큰 문자열은 .credentials 속성에 있습니다.


async def get_current_user_email(token_object: HTTPBearer = Depends(http_bearer_scheme)) -> str:
    """
    JWT 토큰을 검증하고 토큰에서 사용자 이메일을 추출합니다.
    HTTPBearer를 통해 Authorization 헤더에서 토큰을 가져옵니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # token_object는 HTTPBearer 객체이므로, 실제 토큰 문자열은 .credentials 속성에 접근해야 합니다.
        payload = jwt.decode(token_object.credentials,
                             SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")  # 'sub' 클레임에서 이메일 추출
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return email

# 현재 사용자 객체를 DB에서 가져오는 의존성 함수 (이전과 동일)


def get_current_user(
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 로그인된(인증된) 사용자 객체를 데이터베이스에서 조회하여 반환합니다.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user

# 관리자 권한 확인 의존성 함수


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    현재 인증된 사용자가 'admin' 역할을 가지고 있는지 확인합니다.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user
