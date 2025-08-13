# backend/core/security.py

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from dotenv import load_dotenv
import os

from ..repositories.user_repo import UserRepository
from ..repositories.api_key_repo import ApiKeyRepository
from ..models.user import User, UserRole
from ..models.api_key import ApiKey
from ..routers.deps_router import get_db


load_dotenv()

pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/dashboard/auth/login")
http_bearer_scheme = HTTPBearer()


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
    return pwdContext.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwdContext.hash(password)


async def get_current_user_email(token_object: HTTPBearer = Depends(http_bearer_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token_object.credentials,
                             SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return email


def get_current_user(
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
) -> User:
    user_repo = UserRepository(db)
    user = user_repo.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user


async def get_valid_api_key(
        xApiKey: str = Header(..., alias="x-api-key"),
        db: Session = Depends(get_db)
) -> ApiKey:
    """HTTP 헤더에서 'x-api-key'를 추출하여 API 키의 유효성을 검증합니다."""

    apiKeyRepo = ApiKeyRepository(db)
    apiKey = apiKeyRepo.get_active_api_key_by_target_key(xApiKey)

    if not apiKey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="I유효하지 않거나 비활성화된 API 키입니다.",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    return apiKey
