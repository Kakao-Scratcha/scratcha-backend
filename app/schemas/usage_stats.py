from datetime import date, datetime
from pydantic import BaseModel
from typing import List


class UsageStatsResponse(BaseModel):
    """일별 API 사용량 통계 데이터 스키마"""
    date: date
    captchaTotalRequests: int
    captchaSuccessCount: int
    captchaFailCount: int
    captchaTimeoutCount: int
    avgResponseTimeMs: float


class DailyUsageSummary(BaseModel):
    """일간 사용량 요약 스키마"""
    todayRequests: int
    yesterdayRequests: int
    ratioVsYesterday: float
    captchaSuccessCount: int
    captchaFailCount: int


class WeeklyUsageSummary(BaseModel):
    """주간 사용량 요약 스키마"""
    thisWeekRequests: int
    lastWeekRequests: int
    ratioVsLastWeek: float
    captchaSuccessCount: int
    captchaFailCount: int


class MonthlyUsageSummary(BaseModel):
    """월간 사용량 요약 스키마"""
    thisMonthRequests: int
    lastMonthRequests: int
    ratioVsLastMonth: float
    captchaSuccessCount: int
    captchaFailCount: int


class TotalRequests(BaseModel):
    """유저의 전체 캡챠 요청 수"""
    totalRequests: int


class ResultsCounts(BaseModel):
    """성공 수, 실패 수 스키마"""
    captchaSuccessCount: int
    captchaFailCount: int


class UsageDataLog(BaseModel):
    """사용량 데이터 로그"""
    id: int         # 캡챠 로그 ID
    appName: str    # 앱 이름
    key: str        # API 키
    date: datetime  # 캡챠 호출 시간 (=문제 생성 시간)
    result: str     # 캡챠 결과
    ratency: int    # 응답시간 (ms)


class PaginatedUsageDataLog(BaseModel):
    """페이지네이션된 사용량 데이터 로그"""
    items: List[UsageDataLog]   # UsageDataLog를 리스트의 아이템으로 사용
    total: int                  # 전체 로그 개수
    page: int                   # 현재 페이지 번호 (skip / limit + 1)
    size: int                   # 현재 페이지의 항목 개수
