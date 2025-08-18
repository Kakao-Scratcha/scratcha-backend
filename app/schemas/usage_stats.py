from datetime import date
from typing import List, Optional
from pydantic import BaseModel


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


class WeeklyUsageSummary(BaseModel):
    """주간 사용량 요약 스키마"""
    thisWeekRequests: int
    lastWeekRequests: int
    ratioVsLastWeek: float


class MonthlyUsageSummary(BaseModel):
    """월간 사용량 요약 스키마"""
    thisMonthRequests: int
    lastMonthRequests: int
    ratioVsLastMonth: float
