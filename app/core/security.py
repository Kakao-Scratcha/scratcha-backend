# app/core/security.py
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from fastapi import HTTPException, status, Depends, Header
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User, UserRole
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.user_repo import UserRepository
from app.core.config import settings # settings 객체 임포트


# 비밀번호 해싱 및 검증을 위한 bcrypt 컨텍스트
pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 및 Bearer 인증 스키마 정의 (FastAPI 의존성 주입용)
oauth2Scheme = OAuth2PasswordBearer(tokenUrl="/api/dashboard/auth/login")
httpBearerScheme = HTTPBearer()


def createAccessToken(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.

    Args:
        data (dict): 토큰에 담을 클레임(payload) 데이터. 'sub' 키에 사용자 식별자가 포함되어야 합니다.
        expires_delta (timedelta | None, optional): 토큰의 유효 기간. None일 경우 기본값(30분)이 사용됩니다.

    Returns:
        str: 생성된 JWT 문자열.
    """
    # 1. 원본 데이터를 복사하여 페이로드(payload)를 생성합니다。
    toEncode = data.copy()

    # 2. 토큰 만료 시간을 설정합니다.
    # expires_delta가 제공되면 해당 시간만큼, 아니면 기본 설정 시간만큼 현재 UTC 시간에 더합니다.
    if expires_delta:
        expire = datetime.now(settings.TIMEZONE) + expires_delta
    else:
        expire = datetime.now(settings.TIMEZONE) + \
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # 3. 페이로드에 만료 시간('exp') 클레임을 추가합니다.
    toEncode.update({"exp": expire})

    # 4. 최종 페이로드를 사용하여 JWT를 인코딩합니다.
    encodedJwt = jwt.encode(toEncode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # 5. 인코딩된 JWT 문자열을 반환합니다.
    return encodedJwt


def decodeJwtToken(token: str) -> dict:
    """
    JWT 토큰을 디코딩하고 유효성을 검증하여 페이로드(payload)를 반환합니다.

    Args:
        token (str): 검증할 JWT 토큰 문자열.

    Returns:
        dict: 디코딩된 토큰의 페이로드(payload).
    """
    try:
        # 1. JWT 라이브러리를 사용하여 토큰을 디코딩하고 검증합니다.
        # SECRET_KEY와 ALGORITHM을 사용하여 서명을 확인하고, 만료 시간을 자동으로 체크합니다.
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # 2. 검증에 성공하면 페이로드를 반환합니다.
        return payload
    except JWTError:
        # 3. 디코딩 또는 검증 과정에서 오류(JWTError)가 발생하면, 인증 실패로 처리합니다.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# 인증만 필요한 라우터에서 사용: JWT payload(dict) 반환
async def getJwtPayload(token_object: HTTPBearer = Depends(httpBearerScheme)) -> dict:
    """
    FastAPI 의존성 주입을 통해 HTTP 'Authorization' 헤더에서 Bearer 토큰을 추출하고,
    디코딩하여 페이로드(payload)를 반환합니다.

    Args:
        token_object (HTTPBearer, optional): `Depends(httpBearerScheme)`를 통해 주입되는 토큰 객체.

    Returns:
        dict: 검증된 JWT의 페이로드(payload).
    """
    # 1. HTTPBearer 스키마를 통해 'Authorization: Bearer <token>' 헤더에서 토큰 자격증명(credentials)을 추출합니다.
    # 2. 추출된 토큰 문자열을 `decodeJwtToken` 함수에 전달하여 페이로드를 얻고 반환합니다.
    return decodeJwtToken(token_object.credentials)


def getEmailFromPayload(payload: dict) -> str:
    """
    JWT 페이로드(payload)에서 사용자 이메일('sub' 클레임)을 추출합니다.

    Args:
        payload (dict): 디코딩된 JWT 페이로드.

    Returns:
        str: 추출된 사용자 이메일.
    """
    # 1. 페이로드 딕셔너리에서 'sub' 키(subject, 여기서는 이메일)의 값을 가져옵니다.
    email = payload.get("sub")
    # 2. 이메일 값이 없는 경우, 유효하지 않은 토큰으로 간주하고 오류를 발생시킵니다.
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 이메일 정보가 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 3. 이메일 값을 반환합니다.
    return email


# User 객체가 필요한 라우터에서 사용: JWT 토큰에서 사용자 이메일을 추출하고 DB에서 User 객체를 반환합니다.
def getCurrentUser(
    payload: dict = Depends(getJwtPayload),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI 의존성 주입을 통해 현재 인증된 사용자의 `User` 모델 객체를 반환합니다.

    Args:
        payload (dict, optional): `getJwtPayload` 의존성을 통해 얻는 JWT 페이로드.
        db (Session, optional): `get_db` 의존성을 통해 얻는 데이터베이스 세션.

    Returns:
        User: 인증된 사용자의 DB 모델 객체.
    """
    # 1. `getJwtPayload` 의존성으로부터 페이로드를 받아 `getEmailFromPayload`를 호출하여 이메일을 추출합니다.
    email = getEmailFromPayload(payload)
    # 2. 데이터베이스 세션을 사용하여 사용자 리포지토리를 생성합니다.
    user_repo = UserRepository(db)
    # 3. 추출된 이메일로 데이터베이스에서 사용자를 조회합니다.
    user = user_repo.getUserByEmail(email)
    # 4. 사용자를 찾을 수 없으면 오류를 발생시킵니다。
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    # 5. 조회된 사용자 객체를 반환합니다.
    return user


def verifyPassword(plainPassword: str, hashedPassword: str) -> bool:
    """
    입력된 평문 비밀번호와 데이터베이스에 저장된 해시된 비밀번호를 비교합니다.

    Args:
        plainPassword (str): 사용자가 입력한 평문 비밀번호.
        hashedPassword (str): 데이터베이스에 저장된 해시된 비밀번호 문자열.

    Returns:
        bool: 비밀번호가 일치하면 True, 그렇지 않으면 False를 반환합니다.
    """
    # 1. passlib의 CryptContext를 사용하여 평문 비밀번호와 해시를 안전하게 비교합니다.
    return pwdContext.verify(plainPassword, hashedPassword)


def getPasswordHash(password: str) -> str:
    """
    평문 비밀번호를 bcrypt 알고리즘을 사용하여 해시합니다.

    Args:
        password (str): 해시할 평문 비밀번호.

    Returns:
        str: 해시된 비밀번호 문자열.
    """
    # 1. passlib의 CryptContext를 사용하여 비밀번호를 해시합니다.
    return pwdContext.hash(password)


# API Key 인증이 필요한 라우터에서 사용: X-Api-Key 헤더의 유효성 검증
async def getValidApiKey(
    xApiKey: str = Header(..., alias="X-Api-Key"),
    db: Session = Depends(get_db)
) -> ApiKey:
    """
    HTTP 요청 헤더의 'X-Api-Key' 값을 검증하여 유효한 `ApiKey` 모델 객체를 반환합니다.

    Args:
        xApiKey (str, optional): `Header` 의존성을 통해 추출된 'X-Api-Key' 값.
        db (Session, optional): `get_db` 의존성을 통해 얻는 데이터베이스 세션.

    Returns:
        ApiKey: 유효성이 검증된 API 키의 DB 모델 객체.
    """
    # 1. 데이터베이스 세션을 사용하여 API 키 리포지토리를 생성합니다.
    apiKeyRepo = ApiKeyRepository(db)
    # 2. 전달받은 API 키 문자열을 사용하여 활성화된 API 키를 데이터베이스에서 조회합니다.
    apiKey = apiKeyRepo.getActiveApiKeyByTargetKey(xApiKey)

    # 3. 유효한 API 키를 찾지 못한 경우, 인증 오류를 발생시킵니다.
    if not apiKey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 비활성화된 API 키입니다.",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    # 4. 조회된 API 키 객체를 반환합니다.
    return apiKey


def getCurrentAdminUser(current_user: User = Depends(getCurrentUser)) -> User:
    """
    현재 인증된 사용자가 관리자(ADMIN) 권한을 가지고 있는지 확인합니다.

    Args:
        current_user (User, optional): `getCurrentUser` 의존성을 통해 얻는 현재 사용자 객체.

    Returns:
        User: 관리자 권한이 확인된 사용자 객체.
    """
    # 1. `getCurrentUser`를 통해 얻은 사용자 객체의 역할(role)을 확인합니다.
    if current_user.role != UserRole.ADMIN:
        # 2. 역할이 ADMIN이 아니면, 권한 부족 오류를 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    # 3. 관리자임이 확인되면, 해당 사용자 객체를 반환합니다.
    return current_user