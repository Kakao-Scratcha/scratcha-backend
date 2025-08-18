from datetime import date, timedelta
from fastapi import HTTPException, status
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.usage_stats import ResultsCounts, TotalRequests, WeeklyUsageSummary, MonthlyUsageSummary, DailyUsageSummary
from app.models.user import User


class UsageStatsService:
    """
    사용량 통계 관련 비즈니스 로직을 처리하는 서비스입니다.

    이 서비스는 사용자 ID 또는 API 키 ID를 기반으로 다양한 통계 정보를 조회하는 기능을 제공합니다.
    - 사용자 전체의 주간, 월간, 일간 사용량 요약
    - 사용자 전체의 총 요청 수 및 성공/실패 수
    - 특정 API 키의 주간, 월간, 일간 사용량 요약
    - 특정 API 키의 총 요청 수 및 성공/실패 수
    """

    def __init__(self, repo: UsageStatsRepository, api_key_repo: ApiKeyRepository):
        """
        서비스를 초기화합니다.

        Args:
            repo (UsageStatsRepository): 사용량 통계 리포지토리
            api_key_repo (ApiKeyRepository): API 키 리포지토리
        """
        self.repo = repo
        self.api_key_repo = api_key_repo

    def _check_api_key_owner(self, apiKeyId: int, currentUser: User):
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
        api_key = self.api_key_repo.get_key_by_key_id(apiKeyId)
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

    # --- API 키 기준 통계 --- #

    def getWeeklySummaryByApiKey(self, apiKeyId: int, currentUser: User) -> WeeklyUsageSummary:
        """
        API 키 기준: 이번 주와 지난주의 사용량 요약을 반환합니다.
        """
        self._check_api_key_owner(apiKeyId, currentUser)
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
        self._check_api_key_owner(apiKeyId, currentUser)
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
        self._check_api_key_owner(apiKeyId, currentUser)
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
        self._check_api_key_owner(apiKeyId, currentUser)
        total_requests_count = self.repo.getTotalRequestsByApiKey(apiKeyId)
        return TotalRequests(totalRequests=total_requests_count)

    def getResultsCountsByApiKey(self, apiKeyId: int, currentUser: User) -> ResultsCounts:
        """
        API 키 기준: 전체 캡챠 성공 및 실패 수를 조회합니다.
        """
        self._check_api_key_owner(apiKeyId, currentUser)
        success_count, fail_count = self.repo.getResultsCountsByApiKey(
            apiKeyId)
        return ResultsCounts(
            captchaSuccessCount=success_count,
            captchaFailCount=fail_count
        )
