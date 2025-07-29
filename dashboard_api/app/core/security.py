# backend/dashboard_api/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt, JWTError
from passlib.context import CryptContext
import os

# 비밀번호 해싱을 위한 컨텍스트
pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정 (환경 변수에서 가져오는 것이 좋지만, 일단 하드코딩)
# 실제 프로젝트에서는 .env 파일에서 불러오도록 하세요.
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 토큰 만료 시간 (분)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    toEncode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    toEncode.update({"exp": expire})
    encodedJwt = jwt.encode(toEncode, SECRET_KEY, algorithm=ALGORITHM)
    return encodedJwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwdContext.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwdContext.hash(password)
