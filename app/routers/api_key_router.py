# app/routers/api_key_router.py

from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session
from typing import List

from db.session import get_db
from app.services.api_key_service import ApiKeyService
from app.schemas.api_key import ApiKeyResponse
from app.core.security import getCurrentUser
from app.models.user import User

# API 라우터 객체 생성
router = APIRouter(
    prefix="/api-keys",
    tags=["API Keys"],
    responses={404: {"description": "Not found"}},
)


def getApiKeyService(db: Session = Depends(get_db)) -> ApiKeyService:
    """
    FastAPI 의존성 주입을 통해 ApiKeyService 인스턴스를 생성하고 반환합니다.

    Args:
        db (Session, optional): `get_db` 의존성에서 제공하는 데이터베이스 세션.

    Returns:
        ApiKeyService: ApiKeyService의 인스턴스.
    """
    return ApiKeyService(db)


@router.post(
    "/",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 API 키 생성",
    description="특정 애플리케이션에 대한 새로운 API 키를 생성합니다.",
)
def createKey(
    appId: int = Body(..., embed=True, description="API 키를 생성할 애플리케이션의 ID"),
    expiresPolicy: int = Body(
        0, embed=True, description="API 키 만료 정책(일 단위, 0 또는 음수는 무제한)"),
    currentUser: User = Depends(getCurrentUser),
    apiKeyService: ApiKeyService = Depends(getApiKeyService)
):
    """
    애플리케이션 ID(`appId`)를 받아 해당 애플리케이션에 대한 새 API 키를 생성합니다.

    Args:
        appId (int): API 키를 생성할 대상 애플리케이션의 고유 ID.
        expiresPolicy (int): API 키의 만료 정책(일 단위). 0 또는 음수는 무제한을 의미합니다.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        apiKeyService (ApiKeyService): 의존성으로 주입된 API 키 서비스 객체.

    Returns:
        ApiKeyResponse: 생성된 API 키의 상세 정보.
    """
    # 1. 인증된 사용자와 요청된 정보를 바탕으로 API 키 생성 서비스를 호출합니다.
    newApiKey = apiKeyService.createKey(currentUser, appId, expiresPolicy)
    # 2. 생성된 API 키 정보를 반환합니다.
    return newApiKey


@router.get(
    "/all",
    response_model=List[ApiKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="사용자의 모든 API 키 조회",
    description="현재 인증된 사용자가 소유한 모든 API 키 목록을 조회합니다.",
)
def getKeys(
    currentUser: User = Depends(getCurrentUser),
    apiKeyService: ApiKeyService = Depends(getApiKeyService)
):
    """
    현재 인증된 사용자의 모든 API 키 목록을 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        apiKeyService (ApiKeyService): 의존성으로 주입된 API 키 서비스 객체.

    Returns:
        List[ApiKeyResponse]: 사용자의 API 키 목록.
    """
    # 1. 현재 사용자의 모든 API 키를 조회하는 서비스를 호출합니다.
    userKeys = apiKeyService.getKeys(currentUser)
    # 2. 조회된 키 목록을 반환합니다.
    return userKeys


@router.get(
    "/{keyId}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 API 키 상세 조회",
    description="API 키 ID를 사용하여 특정 API 키의 상세 정보를 조회합니다.",
)
def getKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    apiKeyService: ApiKeyService = Depends(getApiKeyService)
):
    """
    API 키 ID(`keyId`)로 특정 API 키의 정보를 조회합니다.

    Args:
        keyId (int): 조회할 API 키의 고유 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        apiKeyService (ApiKeyService): 의존성으로 주입된 API 키 서비스 객체.

    Returns:
        ApiKeyResponse: 조회된 API 키의 상세 정보.
    """
    # 1. 특정 API 키를 조회하는 서비스를 호출합니다.
    apiKey = apiKeyService.getKey(keyId, currentUser)
    # 2. 조회된 키 정보를 반환합니다.
    return apiKey


@router.put(
    "/{keyId}/activate",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 활성화",
    description="지정된 API 키를 활성화 상태로 변경합니다.",
)
def activateKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    apiKeyService: ApiKeyService = Depends(getApiKeyService)
):
    """
    API 키 ID(`keyId`)에 해당하는 API 키를 활성화합니다.

    Args:
        keyId (int): 활성화할 API 키의 고유 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        apiKeyService (ApiKeyService): 의존성으로 주입된 API 키 서비스 객체.

    Returns:
        ApiKeyResponse: 활성화된 API 키의 상세 정보.
    """
    # 1. API 키를 활성화하는 서비스를 호출합니다.
    activatedKey = apiKeyService.activateKey(keyId, currentUser)
    # 2. 변경된 키 정보를 반환합니다.
    return activatedKey


@router.put(
    "/{keyId}/deactivate",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 비활성화",
    description="지정된 API 키를 비활성화 상태로 변경합니다.",
)
def deactivateKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    apiKeyService: ApiKeyService = Depends(getApiKeyService)
):
    """
    API 키 ID(`keyId`)에 해당하는 API 키를 비활성화합니다.

    Args:
        keyId (int): 비활성화할 API 키의 고유 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        apiKeyService (ApiKeyService): 의존성으로 주입된 API 키 서비스 객체.

    Returns:
        ApiKeyResponse: 비활성화된 API 키의 상세 정보.
    """
    # 1. API 키를 비활성화하는 서비스를 호출합니다.
    deactivatedKey = apiKeyService.deactivateKey(keyId, currentUser)
    # 2. 변경된 키 정보를 반환합니다.
    return deactivatedKey


@router.delete(
    "/{keyId}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 삭제",
    description="지정된 API 키를 소프트 삭제(soft-delete) 처리합니다.",
)
def deleteKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    apiKeyService: ApiKeyService = Depends(getApiKeyService)
):
    """
    API 키 ID(`keyId`)에 해당하는 API 키를 소프트 삭제합니다.

    Args:
        keyId (int): 삭제할 API 키의 고유 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        apiKeyService (ApiKeyService): 의존성으로 주입된 API 키 서비스 객체.

    Returns:
        ApiKeyResponse: 삭제 처리된 API 키의 상세 정보.
    """
    # 1. API 키를 삭제하는 서비스를 호출합니다.
    deletedKey = apiKeyService.deleteKey(keyId, currentUser)
    # 2. 변경된 키 정보를 반환합니다.
    return deletedKey
