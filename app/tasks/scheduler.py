import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.config import settings
from db.session import get_db
from app.models.captcha_session import CaptchaSession
from app.models.captcha_log import CaptchaLog, CaptchaResult
from app.repositories.captcha_repo import CaptchaRepository
from app.repositories.usage_stats_repo import UsageStatsRepository

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def cleanup_expired_captcha_sessions():
    """
    3분 이상 경과하고 아직 검증되지 않은 캡챠 세션을 TIMEOUT 처리합니다.
    """
    db: Session = next(get_db())  # Get a new DB session for the task
    try:
        captcha_repo = CaptchaRepository(db)
        usage_stats_repo = UsageStatsRepository(db)

        # 3분 이상 경과한 캡챠 세션 조회
        # createdAt이 timezone-aware datetime 객체이므로, 비교 대상도 timezone-aware여야 함
        timeout_threshold = datetime.now(
            settings.TIMEZONE) - timedelta(minutes=3)

        # CaptchaLog가 없는 세션만 필터링
        expired_sessions = db.query(CaptchaSession).filter(
            CaptchaSession.createdAt < timeout_threshold,
            ~CaptchaSession.captchaLog.any()  # CaptchaLog가 없는 세션 필터링
        ).all()

        if expired_sessions:
            logger.info(f"{len(expired_sessions)} 개의 만료된 세션 발견")

            for session in expired_sessions:
                # Ensure session.createdAt is timezone-aware
                if session.createdAt.tzinfo is None:
                    session.createdAt = settings.TIMEZONE.localize(
                        session.createdAt)

                # TIMEOUT 로그 생성
                latency = datetime.now(settings.TIMEZONE) - session.createdAt
                captcha_repo.createCaptchaLog(
                    session=session,
                    result=CaptchaResult.TIMEOUT,
                    latency_ms=int(latency.total_seconds() * 1000)
                )
                # 사용량 통계 업데이트
                usage_stats_repo.incrementVerificationResult(
                    session.keyId, CaptchaResult.TIMEOUT.value, int(
                        latency.total_seconds() * 1000)
                )
                logger.info(
                    f"세션 만료(TIMEOUT) : [세션 ID={session.id}, 클라이언트 토큰={session.clientToken}]")
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"캡챠 세션 타임아웃 에러: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(cleanup_expired_captcha_sessions,
                      'interval', minutes=1)  # 1분마다 실행
    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown()
