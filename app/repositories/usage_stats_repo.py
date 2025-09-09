from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date, timedelta
from typing import Optional
from fastapi import HTTPException, status

from app.models.usage_stats import UsageStats
from app.models.api_key import ApiKey
from app.models.application import Application
from app.models.captcha_log import CaptchaLog


class UsageStatsRepository:
    def __init__(self, db: Session):
        self.db = db

    def incrementTotalRequests(self, keyId: int):
        """
        특정 API 키에 대한 오늘 날짜의 캡챠 총 요청 수를 1 증가시킵니다.
        오늘 날짜의 통계 데이터가 없으면 새로 생성하고, 있으면 카운트를 업데이트합니다.
        """
        try:
            # 1. 오늘 날짜를 기준으로 해당 API 키의 통계 데이터를 조회합니다.
            today = date.today()
            usageStats = self.db.query(UsageStats).filter(
                UsageStats.keyId == keyId,
                UsageStats.date == today
            ).first()

            # 2. 오늘 날짜의 통계 데이터가 이미 존재하면, 총 요청 수를 1 증가시킵니다.
            if usageStats:
                usageStats.captchaTotalRequests += 1
            # 3. 오늘 날짜의 통계 데이터가 없으면, 새로운 레코드를 생성하고 총 요청 수를 1로 초기화합니다.
            else:
                usageStats = UsageStats(
                    keyId=keyId,
                    date=today,
                    captchaTotalRequests=1,
                    captchaSuccessCount=0,
                    captchaFailCount=0
                )
                self.db.add(usageStats)

            # 4. 변경사항을 데이터베이스 세션에 반영합니다. 실제 커밋은 서비스 레이어에서 처리됩니다.
            self.db.flush([usageStats])

        except Exception as e:
            # 5. 데이터베이스 작업 중 예외 발생 시, 롤백을 유도하고 서버 오류를 발생시킵니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"캡챠 요청 수 업데이트 중 오류가 발생했습니다: {e}"
            )

    def incrementVerificationResult(self, keyId: int, result: str, latencyMs: int):
        """
        특정 API 키에 대한 오늘 날짜의 캡챠 검증 결과를(성공/실패/타임아웃) 1 증가시키고,
        평균 응답 시간 계산을 위한 총 지연 시간과 검증 횟수를 업데이트합니다.
        """
        try:
            # 1. 오늘 날짜의 통계 데이터를 조회합니다.
            today = date.today()
            usageStats = self.db.query(UsageStats).filter(
                UsageStats.keyId == keyId,
                UsageStats.date == today
            ).first()

            # 2. 통계 데이터가 없으면 새로 생성합니다.
            if not usageStats:
                usageStats = UsageStats(
                    keyId=keyId,
                    date=today,
                    captchaTotalRequests=0,
                    captchaSuccessCount=0,
                    captchaFailCount=0,
                    captchaTimeoutCount=0,
                    totalLatencyMs=0,
                    verificationCount=0
                )
                self.db.add(usageStats)

            # 3. 검증 결과에 따라 해당하는 카운트를 1 증가시킵니다.
            if result == "success":
                usageStats.captchaSuccessCount += 1
            elif result == "fail":
                usageStats.captchaFailCount += 1
            elif result == "timeout":
                usageStats.captchaTimeoutCount += 1

            # 4. 평균 응답시간 계산을 위해 총 지연시간과 검증 횟수를 업데이트합니다.
            #    TIMEOUT 결과는 검증 횟수에 포함하지 않습니다.
            usageStats.totalLatencyMs += latencyMs
            if result != "timeout": # TIMEOUT 결과는 지연 시간에 포함하지 않습니다.
                usageStats.verificationCount += 1
            
            if usageStats.verificationCount > 0:
                usageStats.avgResponseTimeMs = usageStats.totalLatencyMs / \
                    usageStats.verificationCount
            else:
                usageStats.avgResponseTimeMs = 0 # 검증 횟수가 0이면 평균 응답 시간도 0

            # 5. 변경사항을 데이터베이스 세션에 반영합니다.
            self.db.flush([usageStats])

        except Exception as e:
            # 6. 데이터베이스 작업 중 예외 발생 시, 서버 오류를 발생시킵니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"캡챠 검증 결과 업데이트 중 오류가 발생했습니다: {e}"
            )

    def getUsageDataLogs(self, keyIds: list[int], startDate: Optional[date] = None, endDate: Optional[date] = None, skip: int = 0, limit: int = 100) -> tuple[list, int]:
        """
        주어진 API 키 목록에 대한 캡챠 사용량 로그를 페이지네이션하여 조회합니다.

        Args:
            keyIds (list[int]): 필터링할 API 키의 ID 리스트.
            startDate (Optional[date]): 조회 시작일. Defaults to None.
            endDate (Optional[date]): 조회 종료일. Defaults to None.
            skip (int): 건너뛸 레코드 수 (페이지네이션용). Defaults to 0.
            limit (int): 가져올 최대 레코드 수 (페이지네이션용). Defaults to 100.

        Returns:
            tuple[list, int]: 조회된 사용량 로그 객체 리스트와 전체 개수.
        """
        try:
            # 1. CaptchaLog, ApiKey, Application 테이블을 조인하여 기본 쿼리를 생성합니다.
            base_query = self.db.query(
                CaptchaLog.id,
                Application.appName,
                ApiKey.key,
                CaptchaLog.created_at,
                CaptchaLog.result,
                CaptchaLog.latency_ms
            ).join(
                ApiKey, CaptchaLog.keyId == ApiKey.id
            ).join(
                Application, ApiKey.appId == Application.id
            )

            # 2. 제공된 API 키 ID 목록이 없으면 빈 결과를 반환합니다.
            if not keyIds:
                return [], 0

            # 3. API 키 ID 목록으로 쿼리를 필터링합니다.
            base_query = base_query.filter(ApiKey.id.in_(keyIds))

            # 4. 시작일과 종료일이 주어지면, 해당 기간으로 쿼리를 필터링합니다.
            if startDate:
                base_query = base_query.filter(
                    CaptchaLog.created_at >= startDate)
            if endDate:
                # 종료일을 포함하기 위해, 종료일 다음 날의 시작 전까지로 범위를 설정합니다.
                base_query = base_query.filter(
                    CaptchaLog.created_at < endDate + timedelta(days=1))

            # 5. 필터링된 전체 로그의 개수를 계산합니다.
            total_count = base_query.count()
            # 6. 페이지네이션(skip, limit)과 정렬을 적용하여 실제 로그 데이터를 조회합니다.
            logs = base_query.order_by(CaptchaLog.created_at.desc()).offset(
                skip).limit(limit).all()

            # 7. 조회된 로그 리스트와 전체 개수를 튜플로 반환합니다.
            return logs, total_count
        except Exception as e:
            # 8. 데이터베이스 조회 중 예외 발생 시, 서버 오류를 발생시킵니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용량 로그 데이터 조회 중 오류가 발생했습니다: {e}"
            )

    def getStatsFromLogs(self, keyIds: list[int], startDate: date, endDate: date):
        """
        captcha_log 테이블에서 직접 시간별 통계를 집계합니다. (일간 통계용)
        이 메소드는 `usage_stats` 테이블에 아직 집계되지 않은 실시간에 가까운 데이터를 제공할 때 유용합니다.

        Args:
            keyIds (list[int]): 조회할 API 키 ID 리스트.
            startDate (date): 조회 시작일.
            endDate (date): 조회 종료일.

        Returns:
            list: 집계된 통계 데이터 리스트.
        """
        try:
            # 1. 시간별로 그룹화하기 위해 DATE_FORMAT 함수를 사용합니다. (MySQL 호환)
            timePeriod = func.DATE_FORMAT(
                CaptchaLog.created_at, '%Y-%m-%dT%H:00:00').label('date')

            # 2. 통계 집계를 위한 기본 쿼리를 작성합니다.
            query = self.db.query(
                timePeriod,  # 그룹화된 시간
                func.coalesce(func.count(CaptchaLog.id), 0).label(
                    'totalRequests'),  # 총 요청 수
                func.coalesce(func.sum(case((CaptchaLog.result == 'success', 1), else_=0)), 0).label(
                    'successCount'),  # 성공 수
                func.coalesce(func.sum(case((CaptchaLog.result == 'fail', 1), else_=0)), 0).label(
                    'failCount'),  # 실패 수
                func.coalesce(func.sum(case((CaptchaLog.result == 'timeout', 1), else_=0)), 0).label(
                    'timeoutCount')  # 타임아웃 수
            ).filter(CaptchaLog.created_at.between(f'{startDate} 00:00:00', f'{endDate} 23:59:59'))

            # 3. 제공된 API 키 ID 목록이 없으면 빈 결과를 반환합니다.
            if not keyIds:
                return []

            # 4. API 키 ID 목록으로 쿼리를 필터링합니다.
            query = query.filter(CaptchaLog.keyId.in_(keyIds))

            # 5. 시간별로 그룹화하고 정렬하여 결과를 반환합니다.
            return query.group_by(timePeriod).order_by(timePeriod).all()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"로그 기반 일일 통계 조회 중 오류: {e}"
            )

    def getAggregatedStats(self, keyIds: list[int], startDate: date, endDate: date, period: str):
        """
        usage_stats 테이블에서 기간별(일간, 월간) 통계를 집계합니다.
        미리 집계된 `usage_stats` 테이블을 사용하므로 `getStatsFromLogs`보다 성능상 이점이 있습니다.

        Args:
            keyIds (list[int]): 조회할 API 키 ID 리스트.
            startDate (date): 조회 시작일.
            endDate (date): 조회 종료일.
            period (str): 집계 기간 타입 ('weekly', 'monthly', 'yearly').

        Returns:
            list: 집계된 통계 데이터 리스트.
        """
        try:
            # 1. 기간 타입에 따라 그룹화할 기준을 설정합니다.
            if period == 'yearly':
                # 연간 조회 시 월별로 그룹화합니다. (MySQL 호환)
                groupPeriod = func.DATE_FORMAT(
                    UsageStats.date, '%Y-%m-01').label('date')
            elif period == 'monthly' or period == 'weekly':
                # 월간 또는 주간 조회 시 일별로 그룹화합니다.
                # usage_stats 테이블은 이미 일별 데이터이므로, date 컬럼을 그룹화 기준으로 사용합니다.
                groupPeriod = UsageStats.date.label('date')
            else:
                raise ValueError("Invalid period type for aggregation")

            # 2. 통계 집계를 위한 기본 쿼리를 작성합니다.
            query = self.db.query(
                groupPeriod,  # 그룹화된 기간
                func.coalesce(func.sum(UsageStats.captchaTotalRequests),
                              0).label('totalRequests'),
                func.coalesce(func.sum(UsageStats.captchaSuccessCount),
                              0).label('successCount'),
                func.coalesce(func.sum(UsageStats.captchaFailCount),
                              0).label('failCount'),
                func.coalesce(func.sum(UsageStats.captchaTimeoutCount), 0).label(
                    'timeoutCount')
            ).filter(UsageStats.date.between(startDate, endDate))

            # 3. 제공된 API 키 ID 목록이 없으면 빈 결과를 반환합니다.
            if not keyIds:
                return []

            # 4. API 키 ID 목록으로 쿼리를 필터링합니다.
            query = query.filter(UsageStats.keyId.in_(keyIds))

            # 5. 기간별로 그룹화하고 정렬하여 결과를 반환합니다.
            return query.group_by(groupPeriod).order_by(groupPeriod).all()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"집계 기반 통계 조회 중 오류: {e}"
            )

    def getTotalRequestsForPeriod(self, keyIds: list[int], startDate: date, endDate: date) -> int:
        """
        지정된 기간 동안의 총 캡챠 요청 수를 합산하여 반환합니다.

        Args:
            keyIds (list[int]): 조회할 API 키 ID 리스트.
            startDate (date): 조회 시작일.
            endDate (date): 조회 종료일.

        Returns:
            int: 총 요청 수.
        """
        # 1. API 키 목록이 없으면 0을 반환합니다.
        if not keyIds:
            return 0

        try:
            # 2. usage_stats 테이블에서 captchaTotalRequests의 합계를 계산합니다.
            totalRequests = self.db.query(
                func.sum(UsageStats.captchaTotalRequests)
            ).filter(
                UsageStats.keyId.in_(keyIds),
                UsageStats.date.between(startDate, endDate)
            ).scalar()

            # 3. 결과가 None이면 0을, 아니면 해당 값을 반환합니다.
            return totalRequests or 0
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"기간별 총 요청 수 조회 중 오류: {e}"
            )

    def getTotalRequests(self, keyIds: list[int]) -> int:
        """
        지정된 API 키들의 전체 캡챠 요청 수를 합산하여 반환합니다.

        Args:
            keyIds (list[int]): 조회할 API 키 ID 리스트.

        Returns:
            int: 총 요청 수.
        """
        # 1. API 키 목록이 없으면 0을 반환합니다.
        if not keyIds:
            return 0

        try:
            # 2. usage_stats 테이블에서 날짜 필터 없이 captchaTotalRequests의 합계를 계산합니다.
            totalRequests = self.db.query(
                func.sum(UsageStats.captchaTotalRequests)
            ).filter(
                UsageStats.keyId.in_(keyIds)
            ).scalar()

            # 3. 결과가 None이면 0을, 아니면 해당 값을 반환합니다.
            return totalRequests or 0
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"전체 요청 수 조회 중 오류: {e}"
            )
