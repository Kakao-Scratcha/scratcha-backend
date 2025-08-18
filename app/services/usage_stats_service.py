from datetime import date, timedelta
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.schemas.usage_stats import UsageStatsResponse, WeeklyUsageSummary, MonthlyUsageSummary, DailyUsageSummary
from sqlalchemy.orm import Session
import calendar


class UsageStatsService:
    """
    사용량 통계 관련 비즈니스 로직을 처리하는 서비스입니다.
    """

    def __init__(self, repo: UsageStatsRepository):
        self.repo = repo

    def getDailyUsageStats(self, userId: int, startDate: date, endDate: date) -> UsageStatsResponse:
        """
        사용자의 일별 사용량 통계를 조회하고 스키마 형식으로 반환합니다.

        Args:
            userId (int): 현재 인증된 사용자의 ID.
            startDate (date): 통계 조회 시작 날짜.
            endDate (date): 통계 조회 종료 날짜.

        Returns:
            UsageStatsResponse: 일별 통계 데이터 리스트를 포함한 응답 객체.
        """
        # 리포지토리 메서드를 호출하여 데이터베이스에서 데이터를 가져옵니다.
        dailyStatsData = self.repo.getDailyUsageByUserId(
            userId, startDate, endDate)

        # Pydantic 스키마를 사용하여 ORM 객체를 직렬화합니다.
        formattedStats = [UsageStatsResponse(date=row[0],
                                             captchaTotalRequests=row[1],
                                             captchaSuccessCount=row[2],
                                             captchaFailCount=row[3],
                                             captchaTimeoutCount=row[4],
                                             avgResponseTimeMs=row[5])
                          for row in dailyStatsData]

        return UsageStatsResponse(daily_stats=formattedStats)

    def getWeeklySummary(self, userId: int) -> WeeklyUsageSummary:
        """
        이번 주, 지난 주 사용량 요약과 추이를 계산하여 반환합니다.
        '이번 주'는 일요일부터 요청 시점까지의 기간을 의미하며,
        '지난 주'는 그 전 주 전체(7일)를 의미합니다.

        Args:
            userId (int): 현재 인증된 사용자의 ID.

        Returns:
            WeeklyUsageSummary: 주간 사용량 요약 객체.
        """
        today = date.today()

        # ISO weekday()는 월요일(1)부터 일요일(7)까지 반환합니다.
        # 이를 일요일(0)부터 시작하는 로직으로 변환합니다.
        # 즉, 일요일은 0, 월요일은 1, ..., 토요일은 6이 됩니다.
        weekdayOffset = today.weekday() + 1
        if weekdayOffset == 7:  # 일요일일 경우
            weekdayOffset = 0

        # 이번 주 (일요일부터 오늘까지) 기간 계산
        thisWeekStartDate = today - timedelta(days=weekdayOffset)
        thisWeekEndDate = today  # 오늘까지의 데이터만 조회

        # 지난 주 (전체 7일) 기간 계산
        lastWeekStartDate = thisWeekStartDate - timedelta(days=7)
        lastWeekEndDate = thisWeekStartDate - timedelta(days=1)

        # 리포지토리에서 각 기간의 총 요청 수 조회
        thisWeekRequests = self.repo.getTotalRequestsForPeriod(
            userId, thisWeekStartDate, thisWeekEndDate
        )
        lastWeekRequests = self.repo.getTotalRequestsForPeriod(
            userId, lastWeekStartDate, lastWeekEndDate
        )

        # 지난 주 대비 이번 주 요청 수 증감률을 백분율로 계산
        if lastWeekRequests > 0:
            ratioChange = round(
                ((thisWeekRequests - lastWeekRequests) / lastWeekRequests) * 100, 2)
        elif thisWeekRequests > 0:
            # 지난 주 요청이 0인데 이번 주 요청이 0보다 크면 100% 증가로 처리
            ratioChange = 100.0
        else:
            # 두 기간 모두 요청이 0건이면 0% 변화
            ratioChange = 0.0

        return WeeklyUsageSummary(
            thisWeekRequests=thisWeekRequests,
            lastWeekRequests=lastWeekRequests,
            ratioVsLastWeek=ratioChange
        )

    def getMonthlySummary(self, userId: int) -> MonthlyUsageSummary:
        """
        이번 달, 지난 달 사용량 요약과 추이를 계산하여 반환합니다.
        '이번 달'은 1일부터 요청 시점까지의 기간을 의미하며,
        '지난 달'은 그 전 달 전체를 의미합니다.

        Args:
            userId (int): 현재 인증된 사용자의 ID.

        Returns:
            MonthlyUsageSummary: 월간 사용량 요약 객체.
        """
        today = date.today()

        # 이번 달 (1일부터 오늘까지) 기간 계산
        thisMonthStartDate = today.replace(day=1)
        thisMonthEndDate = today

        # 지난 달 (전체) 기간 계산
        # 현재 달에서 1달을 빼서 지난 달을 구하고, 지난 달의 마지막 날짜를 구합니다.
        lastMonthEndDate = thisMonthStartDate - timedelta(days=1)
        lastMonthStartDate = lastMonthEndDate.replace(day=1)

        # 리포지토리에서 각 기간의 총 요청 수 조회
        thisMonthRequests = self.repo.getTotalRequestsForPeriod(
            userId, thisMonthStartDate, thisMonthEndDate
        )
        lastMonthRequests = self.repo.getTotalRequestsForPeriod(
            userId, lastMonthStartDate, lastMonthEndDate
        )

        # 지난 달 대비 이번 달 요청 수 증감률을 백분율로 계산
        if lastMonthRequests > 0:
            ratioChange = round(
                ((thisMonthRequests - lastMonthRequests) / lastMonthRequests) * 100, 2)
        elif thisMonthRequests > 0:
            # 지난 달 요청이 0인데 이번 달 요청이 0보다 크면 100% 증가로 처리
            ratioChange = 100.0
        else:
            # 두 기간 모두 요청이 0건이면 0% 변화
            ratioChange = 0.0

        return MonthlyUsageSummary(
            thisMonthRequests=thisMonthRequests,
            lastMonthRequests=lastMonthRequests,
            ratioVsLastMonth=ratioChange
        )

    def getDailySummary(self, userId: int) -> DailyUsageSummary:
        """
        오늘과 어제 사용량 요약과 추이를 계산하여 반환합니다.

        Args:
            userId (int): 현재 인증된 사용자의 ID.

        Returns:
            DailyUsageSummary: 일간 사용량 요약 객체.
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 리포지토리에서 각 기간의 총 요청 수 조회
        todayRequests = self.repo.getTotalRequestsForPeriod(
            userId, today, today)
        yesterdayRequests = self.repo.getTotalRequestsForPeriod(
            userId, yesterday, yesterday)

        # 어제 대비 오늘 요청 수 증감률을 백분율로 계산
        if yesterdayRequests > 0:
            ratioChange = round(
                ((todayRequests - yesterdayRequests) / yesterdayRequests) * 100, 2)
        elif todayRequests > 0:
            # 어제 요청이 0인데 오늘 요청이 0보다 크면 100% 증가로 처리
            ratioChange = 100.0
        else:
            # 두 기간 모두 요청이 0건이면 0% 변화
            ratioChange = 0.0

        return DailyUsageSummary(
            todayRequests=todayRequests,
            yesterdayRequests=yesterdayRequests,
            ratioVsYesterday=ratioChange
        )
