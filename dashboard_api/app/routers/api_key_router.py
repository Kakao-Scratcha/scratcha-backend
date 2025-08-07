# dashboard_api/app/routers/api_key.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from dashboard_api.app.services.api_key_service import ApiKeyService
from dashboard_api.app.routers.deps_router import get_db
from dashboard_api.app.schemas.api_key import ApiKeyResponse
from dashboard_api.app.core.security import get_current_user
from dashboard_api.app.models.user import User

router = APIRouter(prefix="/api-key", tags=["api_key"])


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
def create_key(
    appId: int,  # 애플리케이션 ID
    expiresPolicy: int = 0,  # 만료 정책 (기본값: 0)
    currentUser: User = Depends(get_current_user),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """특정 애플리케이션에 대한 API 키를 생성합니다."""
    return service.create_key(currentUser, appId, expiresPolicy)


@router.get(
    "/all",
    response_model=List[ApiKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="API 키 목록 조회",
    description="현재 인증된 사용자의 모든 API 키 목록을 조회합니다.",
)
def get_keys(
    currentUser: User = Depends(get_current_user),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """현재 인증된 사용자의 모든 API 키를 조회합니다."""
    return service.get_keys(currentUser)


@router.get(
    "/{key_id}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 단일 조회",
    description="API 키 ID로 단일 API 키를 조회합니다.",
)
def get_key(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(get_current_user),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키 ID로 단일 API 키를 조회합니다."""
    return service.get_key(keyId, currentUser)


@router.put(
    "/{key_id}/activate",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 활성화",
    description="API 키를 활성화합니다.",
)
def activate_key(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(get_current_user),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키를 활성화합니다."""
    return service.activate_key(keyId)


@router.put(
    "/{key_id}/deactivate",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 비활성화",
    description="API 키를 비활성화합니다.",
)
def deactivate_key(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(get_current_user),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키를 비활성화합니다."""
    return service.deactivate_key(keyId)


@router.delete(
    "/{key_id}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="API 키 삭제",
    description="API 키를 소프트 삭제합니다.",
)
def delete_key(
    keyId: int,  # API 키 ID
    currentUser: User = Depends(get_current_user),  # 현재 인증된 사용자 정보 가져오기
    service: ApiKeyService = Depends(service)
):
    """API 키를 소프트 삭제합니다."""
    return service.delete_key(keyId, currentUser)
