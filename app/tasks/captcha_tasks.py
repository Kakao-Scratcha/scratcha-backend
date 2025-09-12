# app/tasks/captcha_tasks.py

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException

from app.celery_app import celery_app
from app.core.config import settings
from app.models.captcha_session import CaptchaSession
from app.models.captcha_log import CaptchaResult
from app.schemas.captcha import CaptchaVerificationRequest
from db.session import SessionLocal

import os
import json
import io
import gzip
import boto3
from botocore.config import Config
from pydantic import BaseModel

# 로거 설정
logger = logging.getLogger(__name__)

# ===== KS3/S3 helpers (copied from captcha_service.py) =====


def model_dump_compat(obj, *, exclude_none: bool = True):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=exclude_none)
    if hasattr(obj, "dict"):
        return obj.dict(exclude_none=exclude_none)
    return obj


def _ks3_client():
    cfg = Config(
        s3={"addressing_style": "path" if settings.KS3_FORCE_PATH_STYLE else "virtual"},
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
    )
    session = boto3.session.Session(
        aws_access_key_id=settings.KS3_ACCESS_KEY,
        aws_secret_access_key=settings.KS3_SECRET_KEY,
        region_name=settings.KS3_REGION or "ap-northeast-2",
    )
    return session.client("s3", endpoint_url=settings.KS3_ENDPOINT, config=cfg)


def _make_session_key(session_id: str, gz: bool = True) -> str:
    ts = datetime.now(settings.TIMEZONE).strftime("%Y%m%d-%H%M%S")
    fname = f"{ts}_{session_id}.json" + (".gz" if gz else "")
    return f"{settings.KS3_PREFIX.strip('/')}/{fname}".strip("/")


def _serialize_jsonl_bytes(payload: CaptchaVerificationRequest) -> bytes:
    meta = model_dump_compat(payload.meta, exclude_none=True)
    events = [model_dump_compat(e, exclude_none=True) for e in payload.events]
    lines = [json.dumps({"type": "meta", **meta}, ensure_ascii=False)]
    for ev in events:
        lines.append(json.dumps({"type": "event", **ev}, ensure_ascii=False))
    # Assuming label is not part of CaptchaVerificationRequest for now, or needs to be added
    # if payload.label:
    #     lines.append(json.dumps({"type": "label", **payload.label}, ensure_ascii=False))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _gzip_bytes(raw: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as gz:
        gz.write(raw)
    return buf.getvalue()

def upload_ks3_session(payload: CaptchaVerificationRequest, session_id: str):
    if not settings.ENABLE_KS3 or not settings.KS3_BUCKET or not settings.KS3_ACCESS_KEY or not settings.KS3_SECRET_KEY or not settings.KS3_ENDPOINT:
        missing = []
        if not settings.ENABLE_KS3:
            missing.append("KS3_ENABLE(auto)==False")
        if not settings.KS3_BUCKET:
            missing.append("KS3_BUCKET")
        if not settings.KS3_ACCESS_KEY:
            missing.append("KS3_ACCESS_KEY")
        if not settings.KS3_SECRET_KEY:
            missing.append("KS3_SECRET_KEY")
        if not settings.KS3_ENDPOINT:
            missing.append("KS3_ENDPOINT")
        logger.warning(
            f"S3 업로드 건너뜀: 설정 누락됨: {', '.join(missing)}")
        return (None, None, f"Missing: {', '.join(missing)}")
    try:
        body = _serialize_jsonl_bytes(payload)
        gz = _gzip_bytes(body)
        key = _make_session_key(session_id, gz=True)
        s3 = _ks3_client()
        s3.put_object(
            Bucket=settings.KS3_BUCKET, Key=key, Body=gz,
            ContentType="application/json", ContentEncoding="gzip",
        )
        logger.info(f"KS3 업로드 성공: s3://{settings.KS3_BUCKET}/{key}")
        return (f"s3://{settings.KS3_BUCKET}/{key}", key, len(gz))
    except Exception as e:
        logger.error(f"KS3 업로드 오류: {e}")
        return (None, None, f"upload error: {e}")


@celery_app.task(bind=True)
def verifyCaptchaTask(self, clientToken: str, answer: str, ipAddress: str, userAgent: str, meta: Optional[Dict[str, Any]] = None, events: Optional[List[Dict[str, Any]]] = None):
    """
    Celery를 사용하여 캡챠 답변을 비동기적으로 검증하는 작업입니다.

    이 작업은 API 요청으로부터 분리되어 백그라운드에서 실행되므로,
    검증 프로세스가 길어지더라도 API 응답에 영향을 주지 않습니다.

    Args:
        self (celery.Task): Celery 태스크 인스턴스. `bind=True` 옵션을 통해 주입됩니다.
        clientToken (str): 검증할 캡챠 세션의 고유 클라이언트 토큰입니다.
        answer (str): 사용자가 제출한 답변입니다.
        ipAddress (str): 사용자 요청의 IP 주소입니다.
        userAgent (str): 사용자 요청의 User-Agent 문자열입니다.
        meta (Optional[Dict[str, Any]]): 행동 데이터 메타 정보입니다.
        events (Optional[List[Dict[str, Any]]]): 사용자 행동 이벤트 데이터입니다.

    Returns:
        dict: 검증 결과를 담은 딕셔너리. 성공 시 `CaptchaVerificationResponse` 스키마와 호환됩니다.

    Raises:
        HTTPException: 서비스 로직 내에서 발생하는 특정 오류 상황 (예: 타임아웃, 잘못된 토큰)에 대한 예외입니다.
        Exception: 데이터베이스 오류 등 예측하지 못한 예외 발생 시 기록됩니다.
    """
    # CaptchaService는 DB 세션에 의존하므로, 작업 내에서 직접 임포트하여 순환 참조를 방지합니다.
    from app.services.captcha_service import CaptchaService

    # 모든 작업은 독립적인 데이터베이스 세션을 사용해야 합니다.
    db = SessionLocal()
    try:
        captchaService = CaptchaService(db)
        verificationRequest = CaptchaVerificationRequest(
            answer=answer, meta=meta, events=events)

        # 동기 방식과 동일한 검증 서비스를 호출합니다.
        result = captchaService.verifyCaptchaAnswer(
            clientToken=clientToken,
            request=verificationRequest,
            ipAddress=ipAddress,
            userAgent=userAgent
        )
        # Celery는 직렬화 가능한 결과만 반환할 수 있으므로, Pydantic 모델을 dict로 변환합니다.
        return {
            "result": result.result,
            "message": result.message,
            "confidence": result.confidence,
            "verdict": result.verdict
        }
    except HTTPException as e:
        # 서비스 로직에서 발생한 HTTPException을 Celery 실패 상태로 기록합니다.
        # 클라이언트는 결과 조회 API를 통해 실패 사실과 원인을 알 수 있습니다.
        self.update_state(state='FAILURE', meta={
                          'exc_type': type(e).__name__, 'exc_message': e.detail})
        # Celery 워커 로그에도 에러를 남기기 위해 예외를 다시 발생시킵니다.
        raise e
    except Exception as e:
        # 예측하지 못한 모든 예외를 처리하고 Celery 실패 상태로 기록합니다.
        self.update_state(state='FAILURE', meta={
                          'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise e
    finally:
        # 작업이 성공하든 실패하든, 사용된 데이터베이스 세션은 반드시 닫아줍니다.
        db.close()


@celery_app.task
def uploadBehaviorDataTask(clientToken: str, request_data: Dict[str, Any]):
    """
    행동 데이터를 S3/KS3에 비동기적으로 업로드하는 Celery 작업입니다.
    """
    logger.info(f"클라이언트 토큰 {clientToken}에 대한 행동 데이터 업로드 중...")
    try:
        # Reconstruct CaptchaVerificationRequest from dict
        request = CaptchaVerificationRequest(**request_data)
        upload_ks3_session(request, clientToken)
        logger.info(
            f"클라이언트 토큰 {clientToken}에 대한 행동 데이터 업로드 성공")
    except Exception as e:
        logger.error(
            f"클라이언트 토큰 {clientToken}에 대한 행동 데이터 업로드 오류: {e}")


@celery_app.task
def cleanupExpiredSessionsTask():
    """
    주기적으로 실행되어 만료된 캡챠 세션을 정리하는 작업입니다.

    3분이 지났지만 아직 로그(성공/실패/타임아웃)가 기록되지 않은 세션을 찾아
    TIMEOUT 상태로 처리하고 관련 통계를 업데이트합니다.
    """
    # 모든 작업은 독립적인 데이터베이스 세션을 사용해야 합니다.
    db = SessionLocal()
    try:
        # 데이터베이스와 상호작용하기 위한 Repository들을 초기화합니다.
        from app.repositories.captcha_repo import CaptchaRepository
        from app.repositories.usage_stats_repo import UsageStatsRepository
        captchaRepo = CaptchaRepository(db)
        usageStatsRepo = UsageStatsRepository(db)

        # 현재 시간 기준으로 3분 전 시간을 계산하여 타임아웃 기준점을 설정합니다.
        timeoutThreshold = datetime.now(
            settings.TIMEZONE) - timedelta(minutes=settings.CAPTCHA_TIMEOUT_MINUTES)

        # 타임아웃 기준점을 지났고, 아직 로그(성공/실패/타임아웃)가 없는 세션들을 조회합니다.
        # with_for_update(skip_locked=True)를 사용하여 여러 워커가 동시에 같은 세션을 처리하는 것을 방지합니다.
        # 이미 다른 워커에 의해 잠긴(처리 중인) 세션은 건너뜁니다.
        expiredSessions = db.query(CaptchaSession).filter(
            CaptchaSession.createdAt < timeoutThreshold,
            ~CaptchaSession.captchaLog.any()
        ).with_for_update(skip_locked=True).all()

        if expiredSessions:
            logger.info(f"{len(expiredSessions)}개의 만료된 세션 발견, 타임아웃 처리 시작")

            for session in expiredSessions:
                # 세션 생성 시간이 타임존 정보를 포함하도록 보정합니다.
                if session.createdAt.tzinfo is None:
                    session.createdAt = settings.TIMEZONE.localize(
                        session.createdAt)

                # 지연 시간(latency)을 계산합니다.
                latency = datetime.now(settings.TIMEZONE) - session.createdAt

                # 타임아웃 로그를 생성합니다.
                captchaRepo.createCaptchaLog(
                    session=session,
                    result=CaptchaResult.TIMEOUT,
                    latency_ms=int(latency.total_seconds() * 1000)
                )
                # 타임아웃 발생에 대한 사용량 통계를 업데이트합니다.
                usageStatsRepo.incrementVerificationResult(
                    session.keyId, CaptchaResult.TIMEOUT.value, int(
                        latency.total_seconds() * 1000)
                )
                logger.info(
                    f"세션 만료(TIMEOUT): [세션 ID={session.id}, 클라이언트 토큰={session.clientToken}]")

            # 모든 변경사항을 데이터베이스에 한 번에 커밋합니다.
            db.commit()
    except Exception as e:
        # 오류 발생 시 모든 변경사항을 롤백합니다.
        db.rollback()
        logger.error(f"주기적인 캡챠 세션 정리 작업 중 오류 발생: {e}")
    finally:
        # 작업이 성공하든 실패하든, 사용된 데이터베이스 세션은 반드시 닫아줍니다.
        db.close()