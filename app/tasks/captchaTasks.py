from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from db.session import SessionLocal
from app.repositories.captcha_repo import CaptchaRepository
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.models.captcha_log import CaptchaResult

async def checkAndLogCaptchaTimeouts():
    """
    주기적으로 실행되어 만료되었지만 아직 로그되지 않은 캡챠 세션을 찾아 타임아웃으로 기록합니다.
    """
    db: Session = SessionLocal()
    try:
        captchaRepo = CaptchaRepository(db)
        usageStatsRepo = UsageStatsRepository(db)

        # 3분 이상 경과했지만 아직 로그되지 않은 세션 조회
        timedOutSessions = captchaRepo.getUnloggedTimedOutSessions(timeoutMinutes=3)

        for session in timedOutSessions:
            latency = datetime.utcnow() - session.createdAt
            # CaptchaLog 기록
            captchaRepo.createCaptchaLog(
                session=session,
                result=CaptchaResult.TIMEOUT,
                latency_ms=int(latency.total_seconds() * 1000),
                ipAddress=None,  # 백그라운드 작업이므로 IP/UserAgent는 알 수 없음
                userAgent=None
            )
            # UsageStats 업데이트
            usageStatsRepo.incrementVerificationResult(
                session.keyId, CaptchaResult.TIMEOUT.value, int(latency.total_seconds() * 1000)
            )
        
        db.commit()
        print(f"Logged {len(timedOutSessions)} timed out captcha sessions.")

    except Exception as e:
        db.rollback()
        print(f"Error in checkAndLogCaptchaTimeouts: {e}")
    finally:
        db.close()
