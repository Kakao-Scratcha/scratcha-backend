# app/core/security.py
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from fastapi import HTTPException, status, Depends, Header
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User, UserRole
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.user_repo import UserRepository


load_dotenv()


# 환경 변수에서 비밀키, 알고리즘, 토큰 만료시간을 불러옵니다.
SECRET_KEY = os.getenv(
    "SECRET_KEY", "fallback-super-secret-key")  # JWT 서명에 사용되는 비밀키
ALGORITHM = "HS256"  # JWT 서명 알고리즘
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 액세스 토큰 기본 만료 시간(분)


# 비밀번호 해싱 및 검증을 위한 bcrypt 컨텍스트
pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 및 Bearer 인증 스키마 정의 (FastAPI 의존성 주입용)
oauth2Scheme = OAuth2PasswordBearer(tokenUrl="/api/dashboard/auth/login")
httpBearerScheme = HTTPBearer()


def createAccessToken(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.
    Args:
        data (dict): 토큰에 담을 클레임(예: {"sub": email})
        expires_delta (timedelta | None): 만료 시간 델타(없으면 기본값 사용)
    Returns:
        str: JWT 문자열
    """
    # 토큰에 만료(exp) 클레임 추가
    toEncode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    toEncode.update({"exp": expire})
    # JWT 인코딩 및 반환
    encodedJwt = jwt.encode(toEncode, SECRET_KEY, algorithm=ALGORITHM)
    return encodedJwt


def decodeJwtToken(token: str) -> dict:
    """
    JWT 토큰의 유효성(서명, 만료 등)을 검증하고 payload(dict)를 반환합니다.
    Args:
        token (str): 클라이언트가 보낸 JWT 문자열
    Returns:
        dict: payload
    """
    # JWT 디코드(서명, 만료 등 검증). 실패 시 401 반환
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # JWT 서명 오류, 만료, 포맷 오류 등 모두 401 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# 인증만 필요한 라우터에서 사용: JWT payload(dict) 반환
async def getJwtPayload(token_object: HTTPBearer = Depends(httpBearerScheme)) -> dict:
    """
    HTTPBearer 인증 헤더에서 JWT 토큰을 추출해 payload(dict)를 반환합니다.
    Args:
        token_object (HTTPAuthorizationCredentials): FastAPI HTTPBearer 의존성으로 추출된 토큰 객체
    Returns:
        dict: JWT payload
    """
    # HTTP Authorization 헤더에서 Bearer 토큰 추출 후 decode
    return decodeJwtToken(token_object.credentials)


def getEmailFromPayload(payload: dict) -> str:
    """
    JWT payload(dict)에서 이메일(sub claim)을 추출합니다.
    Args:
        payload (dict): decode_jwt_token 결과 dict
    Returns:
        str: 이메일
    """
    # JWT payload에서 sub(이메일) 추출, 없으면 401
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 이메일 정보가 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


# User 객체가 필요한 라우터에서 사용: JWT 토큰에서 사용자 이메일을 추출하고 DB에서 User 객체를 반환합니다.
def getCurrentUser(
    payload: dict = Depends(getJwtPayload),
    db: Session = Depends(get_db)
) -> User:
    """
    JWT 토큰에서 이메일(sub claim)을 추출하고, 해당 이메일로 DB에서 User 객체를 조회해 반환합니다.
    Args:
        payload (dict): get_jwt_payload로 추출된 JWT payload
        db (Session): SQLAlchemy 세션
    Returns:
        User: 인증된 사용자 객체
    """
    # JWT payload에서 이메일 추출
    email = getEmailFromPayload(payload)
    # DB에서 사용자 조회
    user_repo = UserRepository(db)
    user = user_repo.getUserByEmail(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user


def verifyPassword(plainPassword: str, hashedPassword: str) -> bool:
    """
    평문 비밀번호와 해시된 비밀번호를 비교하여 일치 여부를 반환합니다.
    Args:
        plainPassword (str): 사용자가 입력한 비밀번호
        hashedPassword (str): 저장된 해시 비밀번호
    Returns:
        bool: 일치하면 True
    """
    # bcrypt를 이용한 비밀번호 검증
    return pwdContext.verify(plainPassword, hashedPassword)


def getPasswordHash(password: str) -> str:
    """
    비밀번호를 bcrypt로 해싱하여 반환합니다.
    Args:
        password (str): 평문 비밀번호
    Returns:
        str: 해시 문자열
    """
    # bcrypt를 이용한 비밀번호 해싱
    return pwdContext.hash(password)


# API Key 인증이 필요한 라우터에서 사용: x-api-key 헤더의 유효성 검증
async def getValidApiKey(
    xApiKey: str = Header(..., alias="x-api-key"),
    db: Session = Depends(get_db)
) -> ApiKey:
    """
    HTTP 헤더에서 'x-api-key'를 추출하여 DB에서 유효한 API Key인지 검증합니다.
    Args:
        xApiKey (str): HTTP 헤더에서 추출된 API Key
        db (Session): SQLAlchemy 세션
    Returns:
        ApiKey: 유효한 API Key 객체
    """
    # DB에서 API Key 유효성 검증
    apiKeyRepo = ApiKeyRepository(db)
    apiKey = apiKeyRepo.getActiveApiKeyByTargetKey(xApiKey)

    if not apiKey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 비활성화된 API 키입니다.",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    return apiKey


def getCurrentAdminUser(current_user: User = Depends(getCurrentUser)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user

