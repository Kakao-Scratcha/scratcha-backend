# app/routers/usage_stats_router.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from db.session import get_db
from app.models.user import User
from app.core.security import getAuthenticatedUser # Updated import
from app.services.usage_stats_service import UsageStatsService
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.usage_stats import StatisticsDataResponse, StatisticsLogResponse, RequestCountSummaryResponse, RequestTotalResponse

router = APIRouter(
    prefix="/statistics",
    tags=["Statistics"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/summary",
    response_model=StatisticsDataResponse,
    summary="기간별 통계 조회",
    description="사용자 또는 특정 API 키에 대한 기간별 통계(연/월/주/일)를 조회합니다."
)
def getSummaryStats(
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
    keyId: Optional[int] = Query(
        None, description="통계를 조회할 API 키의 ID. 미지정 시 사용자 전체 키 합산"),
    periodType: str = Query(..., description="조회 기간 타입 (yearly, monthly, weekly, daily)",
                            regex="^(yearly|monthly|weekly|daily)$"),
    startDate: Optional[date] = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    endDate: Optional[date] = Query(None, description="조회 종료일 (YYYY-MM-DD)")
):
    """
    기간별 통계 요약 데이터를 반환합니다.

    - keyId: 특정 API 키의 통계를 원할 경우 지정합니다.
    - periodType: `yearly`, `monthly`, `weekly`, `daily` 중 하나를 선택합니다.
    - startDate, endDate: 조회 기간을 직접 지정하고 싶을 경우 사용합니다. 미지정 시 periodType에 따라 기본값이 적용됩니다.
    """
    # Instantiate service inside the endpoint
    usageStatsService = UsageStatsService(UsageStatsRepository(db), ApiKeyRepository(db))
    data = usageStatsService.getSummary(
        currentUser=authenticatedUser,
        keyId=keyId,
        periodType=periodType,
        startDate=startDate,
        endDate=endDate
    )

    return data


@router.get(
    "/logs",
    response_model=StatisticsLogResponse,
    summary="기간별 로그 조회 (페이지네이션)",
    description="사용자 또는 특정 API 키에 대한 캡챠 사용량 로그를 페이지네이션하여 조회합니다."
)
def getUsageLogs(
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
    keyId: Optional[int] = Query(
        None, description="로그를 조회할 API 키의 ID. 미지정 시 사용자 전체 로그"),
    periodType: str = Query(..., description="조회 기간 타입 (yearly, monthly, weekly, daily)",
                            regex="^(yearly|monthly|weekly|daily)$"),
    startDate: Optional[date] = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    endDate: Optional[date] = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="가져올 최대 항목 수")
):
    """
    기간별 필터링된 사용량 로그 데이터를 페이지네이션하여 반환합니다.

    - keyId: 특정 API 키의 로그를 원할 경우 지정합니다.
    - periodType: `yearly`, `monthly`, `weekly`, `daily` 중 하나를 선택합니다.
    - startDate, endDate: 조회 기간을 직접 지정하고 싶을 경우 사용합니다.
    - skip: 페이지네이션을 위한 오프셋.
    - limit: 페이지네이션을 위한 최대 항목 수.
    """
    # Instantiate service inside the endpoint
    usageStatsService = UsageStatsService(UsageStatsRepository(db), ApiKeyRepository(db))
    data = usageStatsService.getUsageData(
        currentUser=authenticatedUser,
        keyId=keyId,
        periodType=periodType,
        startDate=startDate,
        endDate=endDate,
        skip=skip,
        limit=limit
    )

    return data


@router.get(
    "/requests",
    response_model=RequestCountSummaryResponse,
    summary="기간별 캡챠 요청 수 조회",
    description="일간/주간/월간 캡챠 요청 수를 이전 기간과 비교하여 조회합니다."
)
def getRequestCountSummary(
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
    keyId: Optional[int] = Query(
        None, description="통계를 조회할 API 키의 ID. 미지정 시 사용자 전체 키 합산"),
    periodType: str = Query(..., description="조회 기간 타입 (daily, weekly, monthly)",
                            regex="^(daily|monthly|weekly|daily)$")
):
    # Instantiate service inside the endpoint
    usageStatsService = UsageStatsService(UsageStatsRepository(db), ApiKeyRepository(db))
    data = usageStatsService.getRequestCountSummary(
        currentUser=authenticatedUser,
        keyId=keyId,
        periodType=periodType
    )

    return data


@router.get(
    "/requests/total",
    response_model=RequestTotalResponse,
    summary="전체 캡챠 요청 수 조회",
    description="사용자 또는 특정 API 키의 전체 캡챠 요청 수를 조회합니다."
)
def getTotalRequestCount(
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db), # Direct DB session injection
    keyId: Optional[int] = Query(
        None, description="조회할 API 키의 ID. 미지정 시 사용자 전체 키 합산")
):
    # Instantiate service inside the endpoint
    usageStatsService = UsageStatsService(UsageStatsRepository(db), ApiKeyRepository(db))
    data = usageStatsService.getTotalRequestCount(
        currentUser=authenticatedUser,
        keyId=keyId
    )

    return data