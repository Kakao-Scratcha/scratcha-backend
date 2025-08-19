# app/routers/api_key_router.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from db.session import get_db
from app.services.api_key_service import ApiKeyService
from app.schemas.api_key import ApiKeyResponse
from app.core.security import getCurrentUser
from app.models.user import User

router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
    responses={404: {"description": "Not found"}},
)


def service(db: Session = Depends(get_db)) -> ApiKeyService:
    """API 키 서비스 인스턴스를 생성합니다."""
    return ApiKeyService(db)


@router.post(
    "/",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="API 키 생성",
    description="특정 애플리케이션에 대한 API 키를 생성합니다.",
)
def createKey(
    appId: int,  # 애플리케이션 ID
    expiresPolicy: int = 0,  # 만료 정책 (기본값: 0)
    currentUser: User = Depends(getCurrentUser),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """특정 애플리케이션에 대한 API 키를 생성합니다."""
    return service.createKey(currentUser, appId, expiresPolicy)


@router.get(
    "/all",
    response_model=List[ApiKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="API 키 목록 조회",
    description="현재 인증된 사용자의 모든 API 키 목록을 조회합니다.",
)
def getKeys(
    currentUser: User = Depends(getCurrentUser),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """현재 인증된 사용자의 모든 API 키를 조회합니다."""
    return service.getKeys(currentUser)


@router.get(
    "/{keyId}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 단일 조회",
    description="API 키 ID로 단일 API 키를 조회합니다.",
)
def getKey(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(getCurrentUser),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키 ID로 단일 API 키를 조회합니다."""
    return service.getKey(keyId, currentUser)


@router.put(
    "/{keyId}/activate",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 활성화",
    description="API 키를 활성화합니다.",
)
def activateKey(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(getCurrentUser),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키를 활성화합니다."""
    return service.activateKey(keyId)


@router.put(
    "/{keyId}/deactivate",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 비활성화",
    description="API 키를 비활성화합니다.",
)
def deactivateKey(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(getCurrentUser),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키를 비활성화합니다."""
    return service.deactivateKey(keyId)


@router.delete(
    "/{keyId}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 삭제",
    description="API 키를 소프트 삭제합니다.",
)
def deleteKey(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(getCurrentUser),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키를 소프트 삭제합니다."""
    return service.deleteKey(keyId, currentUser)
