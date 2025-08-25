# services/usage_stats_service.py

from datetime import date, timedelta
from typing import List
from fastapi import HTTPException, status
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.usage_stats import ResultsCounts, TotalRequests, WeeklyUsageSummary, MonthlyUsageSummary, DailyUsageSummary, UsageDataLog, PaginatedUsageDataLog
from app.models.user import User


class UsageStatsService:
    """
    사용량 통계 관련 비즈니스 로직을 처리하는 서비스 클래스입니다.
    """

    def __init__(self, repo: UsageStatsRepository, api_key_repo: ApiKeyRepository):
        """
        UsageStatsService의 생성자입니다.

        Args:
            repo (UsageStatsRepository): 사용량 통계 리포지토리 객체.
            api_key_repo (ApiKeyRepository): API 키 리포지토리 객체.
        """
        self.repo = repo
        self.api_key_repo = api_key_repo

    def _checkApiKeyOwner(self, keyId: int, currentUser: User):
        """
        API 키의 소유권을 확인합니다.

        요청한 사용자가 해당 API 키의 실제 소유자인지 확인하여, 권한이 없는 경우
        HTTP 403 Forbidden 예외를 발생시킵니다.

        Args:
            keyId (int): 확인할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Raises:
            HTTPException: API 키가 존재하지 않거나 사용자에게 소유권이 없는 경우.
        """
        # 1. API 키 ID를 사용하여 API 키 정보를 조회합니다.
        api_key = self.api_key_repo.getKeyByKeyId(keyId)
        # 2. API 키가 존재하지 않거나, 해당 키의 애플리케이션 소유자와 현재 사용자가 다를 경우 예외를 발생시킵니다.
        if not api_key or api_key.application.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 API 키에 접근할 권한이 없습니다."
            )

    def getDailySummary(self, userId: int) -> DailyUsageSummary:
        """
        사용자 기준: 오늘과 어제의 사용량 요약을 반환합니다.

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            DailyUsageSummary: 일일 사용량 요약 정보.
        """
        # 1. 오늘과 어제 날짜를 계산합니다.
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 2. 오늘과 어제의 사용량 통계를 각각 조회합니다.
        today_total, today_success, today_fail = self.repo.getSummaryForPeriod(
            userId, today, today)
        yesterday_total, _, _ = self.repo.getSummaryForPeriod(
            userId, yesterday, yesterday)

        # 3. 어제 대비 오늘 사용량의 변화율을 계산합니다.
        if yesterday_total > 0:
            ratioChange = round(
                ((today_total - yesterday_total) / yesterday_total) * 100, 2)
        elif today_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        # 4. 계산된 결과를 DailyUsageSummary 모델에 담아 반환합니다.
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

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            WeeklyUsageSummary: 주간 사용량 요약 정보.
        """
        # 1. 이번 주와 지난주의 시작 및 종료 날짜를 계산합니다.
        today = date.today()
        weekdayOffset = today.weekday() + 1
        if weekdayOffset == 7:
            weekdayOffset = 0

        thisWeekStartDate = today - timedelta(days=weekdayOffset)
        thisWeekEndDate = today
        lastWeekStartDate = thisWeekStartDate - timedelta(days=7)
        lastWeekEndDate = thisWeekStartDate - timedelta(days=1)

        # 2. 이번 주와 지난주의 사용량 통계를 각각 조회합니다.
        thisWeek_total, thisWeek_success, thisWeek_fail = self.repo.getSummaryForPeriod(
            userId, thisWeekStartDate, thisWeekEndDate
        )
        lastWeek_total, _, _ = self.repo.getSummaryForPeriod(
            userId, lastWeekStartDate, lastWeekEndDate
        )

        # 3. 지난주 대비 이번 주 사용량의 변화율을 계산합니다.
        if lastWeek_total > 0:
            ratioChange = round(
                ((thisWeek_total - lastWeek_total) / lastWeek_total) * 100, 2)
        elif thisWeek_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        # 4. 계산된 결과를 WeeklyUsageSummary 모델에 담아 반환합니다.
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

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            MonthlyUsageSummary: 월간 사용량 요약 정보.
        """
        # 1. 이번 달과 지난달의 시작 및 종료 날짜를 계산합니다.
        today = date.today()
        thisMonthStartDate = today.replace(day=1)
        thisMonthEndDate = today
        lastMonthEndDate = thisMonthStartDate - timedelta(days=1)
        lastMonthStartDate = lastMonthEndDate.replace(day=1)

        # 2. 이번 달과 지난달의 사용량 통계를 각각 조회합니다.
        thisMonth_total, thisMonth_success, thisMonth_fail = self.repo.getSummaryForPeriod(
            userId, thisMonthStartDate, thisMonthEndDate
        )
        lastMonth_total, _, _ = self.repo.getSummaryForPeriod(
            userId, lastMonthStartDate, lastMonthEndDate
        )

        # 3. 지난달 대비 이번 달 사용량의 변화율을 계산합니다.
        if lastMonth_total > 0:
            ratioChange = round(
                ((thisMonth_total - lastMonth_total) / lastMonth_total) * 100, 2)
        elif thisMonth_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        # 4. 계산된 결과를 MonthlyUsageSummary 모델에 담아 반환합니다.
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

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            TotalRequests: 전체 요청 수를 담은 객체.
        """
        # 1. 리포지토리를 통해 전체 요청 수를 조회합니다.
        total_requests_count = self.repo.getTotalRequests(userId)
        # 2. 조회된 결과를 TotalRequests 모델에 담아 반환합니다.
        return TotalRequests(totalRequests=total_requests_count)

    def getResultsCounts(self, userId: int) -> ResultsCounts:
        """
        사용자 기준: 전체 캡챠 성공 및 실패 수를 조회합니다.

        Args:
            userId (int): 조회할 사용자의 ID.

        Returns:
            ResultsCounts: 성공 및 실패 횟수를 담은 객체.
        """
        # 1. 리포지토리를 통해 성공 및 실패 횟수를 조회합니다.
        success_count, fail_count = self.repo.getResultsCounts(userId)
        # 2. 조회된 결과를 ResultsCounts 모델에 담아 반환합니다.
        return ResultsCounts(
            captchaSuccessCount=success_count,
            captchaFailCount=fail_count
        )

    def getUsageData(self, currentUser: User, keyId: int = None, skip: int = 0, limit: int = 100) -> PaginatedUsageDataLog:
        """
        사용자 또는 API 키별 캡챠 사용량 로그를 페이지네이션하여 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.
            keyId (int, optional): API 키의 ID. None이면 사용자 전체 로그를 조회합니다. Defaults to None.
            skip (int): 건너뛸 레코드 수. Defaults to 0.
            limit (int): 가져올 최대 레코드 수. Defaults to 100.

        Returns:
            PaginatedUsageDataLog: 페이지네이션된 사용량 로그 객체.
        """
        # 1. keyId가 주어진 경우, 해당 API 키에 대한 소유권을 확인합니다.
        if keyId:
            self._checkApiKeyOwner(keyId, currentUser)
            # 2. API 키 ID를 기준으로 사용량 로그와 전체 개수를 조회합니다.
            logs, total_count = self.repo.getUsageDataLogs(
                keyId=keyId, skip=skip, limit=limit)
        else:
            # 3. 사용자 ID를 기준으로 사용량 로그와 전체 개수를 조회합니다.
            logs, total_count = self.repo.getUsageDataLogs(
                userId=currentUser.id, skip=skip, limit=limit)

        # 4. 조회된 로그 데이터를 UsageDataLog 스키마에 맞게 변환합니다.
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

        # 5. 페이지네이션 결과를 PaginatedUsageDataLog 모델에 담아 반환합니다.
        return PaginatedUsageDataLog(
            items=items,
            total=total_count,
            page=skip // limit + 1,
            size=len(items)
        )

    # --- API 키 기준 통계 --- #

    def getWeeklySummaryByApiKey(self, keyId: int, currentUser: User) -> WeeklyUsageSummary:
        """
        API 키 기준: 이번 주와 지난주의 사용량 요약을 반환합니다.

        Args:
            keyId (int): 조회할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            WeeklyUsageSummary: 주간 사용량 요약 정보.
        """
        # 1. API 키 소유권을 확인합니다.
        self._checkApiKeyOwner(keyId, currentUser)
        # 2. 이번 주와 지난주의 시작 및 종료 날짜를 계산합니다.
        today = date.today()
        weekdayOffset = today.weekday() + 1
        if weekdayOffset == 7:
            weekdayOffset = 0
        thisWeekStartDate = today - timedelta(days=weekdayOffset)
        thisWeekEndDate = today
        lastWeekStartDate = thisWeekStartDate - timedelta(days=7)
        lastWeekEndDate = thisWeekStartDate - timedelta(days=1)

        # 3. API 키를 기준으로 이번 주와 지난주의 사용량 통계를 각각 조회합니다.
        thisWeek_total, thisWeek_success, thisWeek_fail = self.repo.getSummaryForPeriodByApiKey(
            keyId, thisWeekStartDate, thisWeekEndDate
        )
        lastWeek_total, _, _ = self.repo.getSummaryForPeriodByApiKey(
            keyId, lastWeekStartDate, lastWeekEndDate
        )

        # 4. 지난주 대비 이번 주 사용량의 변화율을 계산합니다.
        if lastWeek_total > 0:
            ratioChange = round(
                ((thisWeek_total - lastWeek_total) / lastWeek_total) * 100, 2)
        elif thisWeek_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        # 5. 계산된 결과를 WeeklyUsageSummary 모델에 담아 반환합니다.
        return WeeklyUsageSummary(
            thisWeekRequests=thisWeek_total,
            lastWeekRequests=lastWeek_total,
            ratioVsLastWeek=ratioChange,
            captchaSuccessCount=thisWeek_success,
            captchaFailCount=thisWeek_fail
        )

    def getMonthlySummaryByApiKey(self, keyId: int, currentUser: User) -> MonthlyUsageSummary:
        """
        API 키 기준: 이번 달과 지난달의 사용량 요약을 반환합니다.

        Args:
            keyId (int): 조회할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            MonthlyUsageSummary: 월간 사용량 요약 정보.
        """
        # 1. API 키 소유권을 확인합니다.
        self._checkApiKeyOwner(keyId, currentUser)
        # 2. 이번 달과 지난달의 시작 및 종료 날짜를 계산합니다.
        today = date.today()
        thisMonthStartDate = today.replace(day=1)
        thisMonthEndDate = today
        lastMonthEndDate = thisMonthStartDate - timedelta(days=1)
        lastMonthStartDate = lastMonthEndDate.replace(day=1)

        # 3. API 키를 기준으로 이번 달과 지난달의 사용량 통계를 각각 조회합니다.
        thisMonth_total, thisMonth_success, thisMonth_fail = self.repo.getSummaryForPeriodByApiKey(
            keyId, thisMonthStartDate, thisMonthEndDate
        )
        lastMonth_total, _, _ = self.repo.getSummaryForPeriodByApiKey(
            keyId, lastMonthStartDate, lastMonthEndDate
        )

        # 4. 지난달 대비 이번 달 사용량의 변화율을 계산합니다.
        if lastMonth_total > 0:
            ratioChange = round(
                ((thisMonth_total - lastMonth_total) / lastMonth_total) * 100, 2)
        elif thisMonth_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        # 5. 계산된 결과를 MonthlyUsageSummary 모델에 담아 반환합니다.
        return MonthlyUsageSummary(
            thisMonthRequests=thisMonth_total,
            lastMonthRequests=lastMonth_total,
            ratioVsLastMonth=ratioChange,
            captchaSuccessCount=thisMonth_success,
            captchaFailCount=thisMonth_fail
        )

    def getDailySummaryByApiKey(self, keyId: int, currentUser: User) -> DailyUsageSummary:
        """
        API 키 기준: 오늘과 어제의 사용량 요약을 반환합니다.

        Args:
            keyId (int): 조회할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            DailyUsageSummary: 일일 사용량 요약 정보.
        """
        # 1. API 키 소유권을 확인합니다.
        self._checkApiKeyOwner(keyId, currentUser)
        # 2. 오늘과 어제 날짜를 계산합니다.
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 3. API 키를 기준으로 오늘과 어제의 사용량 통계를 각각 조회합니다.
        today_total, today_success, today_fail = self.repo.getSummaryForPeriodByApiKey(
            keyId, today, today)
        yesterday_total, _, _ = self.repo.getSummaryForPeriodByApiKey(
            keyId, yesterday, yesterday)

        # 4. 어제 대비 오늘 사용량의 변화율을 계산합니다.
        if yesterday_total > 0:
            ratioChange = round(
                ((today_total - yesterday_total) / yesterday_total) * 100, 2)
        elif today_total > 0:
            ratioChange = 100.0
        else:
            ratioChange = 0.0

        # 5. 계산된 결과를 DailyUsageSummary 모델에 담아 반환합니다.
        return DailyUsageSummary(
            todayRequests=today_total,
            yesterdayRequests=yesterday_total,
            ratioVsYesterday=ratioChange,
            captchaSuccessCount=today_success,
            captchaFailCount=today_fail
        )

    def getTotalRequestsByApiKey(self, keyId: int, currentUser: User) -> TotalRequests:
        """
        API 키 기준: 전체 캡챠 요청 수를 조회합니다.

        Args:
            keyId (int): 조회할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            TotalRequests: 전체 요청 수를 담은 객체.
        """
        # 1. API 키 소유권을 확인합니다.
        self._checkApiKeyOwner(keyId, currentUser)
        # 2. 리포지토리를 통해 전체 요청 수를 조회합니다.
        total_requests_count = self.repo.getTotalRequestsByApiKey(keyId)
        # 3. 조회된 결과를 TotalRequests 모델에 담아 반환합니다.
        return TotalRequests(totalRequests=total_requests_count)

    def getResultsCountsByApiKey(self, keyId: int, currentUser: User) -> ResultsCounts:
        """
        API 키 기준: 전체 캡챠 성공 및 실패 수를 조회합니다.

        Args:
            keyId (int): 조회할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Returns:
            ResultsCounts: 성공 및 실패 횟수를 담은 객체.
        """
        # 1. API 키 소유권을 확인합니다.
        self._checkApiKeyOwner(keyId, currentUser)
        # 2. 리포지토리를 통해 성공 및 실패 횟수를 조회합니다.
        success_count, fail_count = self.repo.getResultsCountsByApiKey(
            keyId)
        # 3. 조회된 결과를 ResultsCounts 모델에 담아 반환합니다.
        return ResultsCounts(
            captchaSuccessCount=success_count,
            captchaFailCount=fail_count
        )
