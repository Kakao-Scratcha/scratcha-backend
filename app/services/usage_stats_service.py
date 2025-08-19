from datetime import date, timedelta
from typing import List
from fastapi import HTTPException, status
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.usage_stats import ResultsCounts, TotalRequests, WeeklyUsageSummary, MonthlyUsageSummary, DailyUsageSummary, UsageDataLog, PaginatedUsageDataLog
from app.models.user import User


class UsageStatsService:

    def __init__(self, repo: UsageStatsRepository, api_key_repo: ApiKeyRepository):
        self.repo = repo
        self.api_key_repo = api_key_repo

    def _checkApiKeyOwner(self, apiKeyId: int, currentUser: User):
        """
        API 키의 소유권을 확인합니다.

        요청한 사용자가 해당 API 키의 실제 소유자인지 확인하여, 권한이 없는 경우
        HTTP 403 Forbidden 예외를 발생시킵니다.

        Args:
            apiKeyId (int): 확인할 API 키의 ID
            currentUser (User): 현재 인증된 사용자 객체

        Raises:
            HTTPException: API 키가 존재하지 않거나 사용자에게 소유권이 없는 경우
        """
        api_key = self.api_key_repo.getKeyByKeyId(apiKeyId)
        if not api_key or api_key.application.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this API key."
            )

    def getDailySummary(self, userId: int) -> DailyUsageSummary:
        """
        사용자 기준: 오늘과 어제의 사용량 요약을 반환합니다.
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        today_total, today_success, today_fail = self.repo.getSummaryForPeriod(
            userId, today, today)
        yesterday_total, _, _ = self.repo.getSummaryForPeriod(
            userId, yesterday, yesterday)

        if yesterday_total > 0:
            ratioChange = round(
                ((today_total - yesterday_total) / yesterday_total) * 100, 2)
        elif today_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        return DailyUsageSummary(
            todayRequests=today_total,
            yesterdayRequests=yesterday_total,
            ratioVsYesterday=ratioChange,
            captchaSuccessCount=today_success,
            captchaFailCount=today_fail
        )

    def getWeeklySummary(self, userId: int) -> WeeklyUsageSummary:
        """
        사용자 기준: 이번 주와 지난주의 사용량 요약을 반환합니다.
        """
        today = date.today()
        weekdayOffset = today.weekday() + 1
        if weekdayOffset == 7:
            weekdayOffset = 0

        thisWeekStartDate = today - timedelta(days=weekdayOffset)
        thisWeekEndDate = today
        lastWeekStartDate = thisWeekStartDate - timedelta(days=7)
        lastWeekEndDate = thisWeekStartDate - timedelta(days=1)

        thisWeek_total, thisWeek_success, thisWeek_fail = self.repo.getSummaryForPeriod(
            userId, thisWeekStartDate, thisWeekEndDate
        )
        lastWeek_total, _, _ = self.repo.getSummaryForPeriod(
            userId, lastWeekStartDate, lastWeekEndDate
        )

        if lastWeek_total > 0:
            ratioChange = round(
                ((thisWeek_total - lastWeek_total) / lastWeek_total) * 100, 2)
        elif thisWeek_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        return WeeklyUsageSummary(
            thisWeekRequests=thisWeek_total,
            lastWeekRequests=lastWeek_total,
            ratioVsLastWeek=ratioChange,
            captchaSuccessCount=thisWeek_success,
            captchaFailCount=thisWeek_fail
        )

    def getMonthlySummary(self, userId: int) -> MonthlyUsageSummary:
        """
        사용자 기준: 이번 달과 지난달의 사용량 요약을 반환합니다.
        """
        today = date.today()
        thisMonthStartDate = today.replace(day=1)
        thisMonthEndDate = today
        lastMonthEndDate = thisMonthStartDate - timedelta(days=1)
        lastMonthStartDate = lastMonthEndDate.replace(day=1)

        thisMonth_total, thisMonth_success, thisMonth_fail = self.repo.getSummaryForPeriod(
            userId, thisMonthStartDate, thisMonthEndDate
        )
        lastMonth_total, _, _ = self.repo.getSummaryForPeriod(
            userId, lastMonthStartDate, lastMonthEndDate
        )

        if lastMonth_total > 0:
            ratioChange = round(
                ((thisMonth_total - lastMonth_total) / lastMonth_total) * 100, 2)
        elif thisMonth_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        return MonthlyUsageSummary(
            thisMonthRequests=thisMonth_total,
            lastMonthRequests=lastMonth_total,
            ratioVsLastMonth=ratioChange,
            captchaSuccessCount=thisMonth_success,
            captchaFailCount=thisMonth_fail
        )

    def getTotalRequests(self, userId: int) -> TotalRequests:
        """
        사용자 기준: 전체 캡챠 요청 수를 조회합니다.
        """
        total_requests_count = self.repo.getTotalRequests(userId)
        return TotalRequests(totalRequests=total_requests_count)

    def getResultsCounts(self, userId: int) -> ResultsCounts:
        """
        사용자 기준: 전체 캡챠 성공 및 실패 수를 조회합니다.
        """
        success_count, fail_count = self.repo.getResultsCounts(userId)
        return ResultsCounts(
            captchaSuccessCount=success_count,
            captchaFailCount=fail_count
        )

    def getUsageData(self, currentUser: User, apiKeyId: int = None, skip: int = 0, limit: int = 100) -> PaginatedUsageDataLog:
        """
        사용자 또는 API 키별 캡챠 사용량 로그를 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.
            apiKeyId (int, optional): API 키의 ID. Defaults to None.
            skip (int): 건너뛸 레코드 수. Defaults to 0.
            limit (int): 가져올 최대 레코드 수. Defaults to 100.

        Returns:
            PaginatedUsageDataLog: 페이지네이션된 사용량 로그 객체.
        """
        if apiKeyId:
            self._checkApiKeyOwner(apiKeyId, currentUser)
            logs, total_count = self.repo.getUsageDataLogs(
                apiKeyId=apiKeyId, skip=skip, limit=limit)
        else:
            logs, total_count = self.repo.getUsageDataLogs(
                userId=currentUser.id, skip=skip, limit=limit)

        items = [
            UsageDataLog(
                id=log[0],
                appName=log[1],
                key=log[2],
                date=log[3],
                result=log[4],
                ratency=log[5]
            )
            for log in logs
        ]

        return PaginatedUsageDataLog(
            items=items,                # UsageDataLog를 리스트의 아이템으로 사용
            total=total_count,          # 전체 로그 개수
            page=skip // limit + 1,     # # 현재 페이지 번호 (skip / limit + 1)
            size=len(items)             # 현재 페이지의 항목 개수
        )

    # --- API 키 기준 통계 --- #

    def getWeeklySummaryByApiKey(self, apiKeyId: int, currentUser: User) -> WeeklyUsageSummary:
        """
        API 키 기준: 이번 주와 지난주의 사용량 요약을 반환합니다.
        """
        self._checkApiKeyOwner(apiKeyId, currentUser)
        today = date.today()
        weekdayOffset = today.weekday() + 1
        if weekdayOffset == 7:
            weekdayOffset = 0
        thisWeekStartDate = today - timedelta(days=weekdayOffset)
        thisWeekEndDate = today
        lastWeekStartDate = thisWeekStartDate - timedelta(days=7)
        lastWeekEndDate = thisWeekStartDate - timedelta(days=1)

        thisWeek_total, thisWeek_success, thisWeek_fail = self.repo.getSummaryForPeriodByApiKey(
            apiKeyId, thisWeekStartDate, thisWeekEndDate
        )
        lastWeek_total, _, _ = self.repo.getSummaryForPeriodByApiKey(
            apiKeyId, lastWeekStartDate, lastWeekEndDate
        )

        if lastWeek_total > 0:
            ratioChange = round(
                ((thisWeek_total - lastWeek_total) / lastWeek_total) * 100, 2)
        elif thisWeek_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        return WeeklyUsageSummary(
            thisWeekRequests=thisWeek_total,
            lastWeekRequests=lastWeek_total,
            ratioVsLastWeek=ratioChange,
            captchaSuccessCount=thisWeek_success,
            captchaFailCount=thisWeek_fail
        )

    def getMonthlySummaryByApiKey(self, apiKeyId: int, currentUser: User) -> MonthlyUsageSummary:
        """
        API 키 기준: 이번 달과 지난달의 사용량 요약을 반환합니다.
        """
        self._checkApiKeyOwner(apiKeyId, currentUser)
        today = date.today()
        thisMonthStartDate = today.replace(day=1)
        thisMonthEndDate = today
        lastMonthEndDate = thisMonthStartDate - timedelta(days=1)
        lastMonthStartDate = lastMonthEndDate.replace(day=1)

        thisMonth_total, thisMonth_success, thisMonth_fail = self.repo.getSummaryForPeriodByApiKey(
            apiKeyId, thisMonthStartDate, thisMonthEndDate
        )
        lastMonth_total, _, _ = self.repo.getSummaryForPeriodByApiKey(
            apiKeyId, lastMonthStartDate, lastMonthEndDate
        )

        if lastMonth_total > 0:
            ratioChange = round(
                ((thisMonth_total - lastMonth_total) / lastMonth_total) * 100, 2)
        elif thisMonth_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        return MonthlyUsageSummary(
            thisMonthRequests=thisMonth_total,
            lastMonthRequests=lastMonth_total,
            ratioVsLastMonth=ratioChange,
            captchaSuccessCount=thisMonth_success,
            captchaFailCount=thisMonth_fail
        )

    def getDailySummaryByApiKey(self, apiKeyId: int, currentUser: User) -> DailyUsageSummary:
        """
        API 키 기준: 오늘과 어제의 사용량 요약을 반환합니다.
        """
        self._checkApiKeyOwner(apiKeyId, currentUser)
        today = date.today()
        yesterday = today - timedelta(days=1)

        today_total, today_success, today_fail = self.repo.getSummaryForPeriodByApiKey(
            apiKeyId, today, today)
        yesterday_total, _, _ = self.repo.getSummaryForPeriodByApiKey(
            apiKeyId, yesterday, yesterday)

        if yesterday_total > 0:
            ratioChange = round(
                ((today_total - yesterday_total) / yesterday_total) * 100, 2)
        elif today_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        return DailyUsageSummary(
            todayRequests=today_total,
            yesterdayRequests=yesterday_total,
            ratioVsYesterday=ratioChange,
            captchaSuccessCount=today_success,
            captchaFailCount=today_fail
        )

    def getTotalRequestsByApiKey(self, apiKeyId: int, currentUser: User) -> TotalRequests:
        """
        API 키 기준: 전체 캡챠 요청 수를 조회합니다.
        """
        self._checkApiKeyOwner(apiKeyId, currentUser)
        total_requests_count = self.repo.getTotalRequestsByApiKey(apiKeyId)
        return TotalRequests(totalRequests=total_requests_count)

    def getResultsCountsByApiKey(self, apiKeyId: int, currentUser: User) -> ResultsCounts:
        """
        API 키 기준: 전체 캡챠 성공 및 실패 수를 조회합니다.
        """
        self._checkApiKeyOwner(apiKeyId, currentUser)
        success_count, fail_count = self.repo.getResultsCountsByApiKey(
            apiKeyId)
        return ResultsCounts(
            captchaSuccessCount=success_count,
            captchaFailCount=fail_count
        )
