# app/core/ks3.py

import logging
import json
import io
import gzip
import boto3
from botocore.config import Config
from datetime import datetime
from typing import Dict, Any, List

from app.core.config import settings
from app.schemas.event import EventChunk
# CaptchaVerificationRequest 스키마 임포트
from app.schemas.captcha import CaptchaVerificationRequest

logger = logging.getLogger(__name__)


def _get_ks3_client():
    """KS3 접속을 위한 boto3 S3 클라이언트를 생성하고 반환합니다."""
    # KS3 설정이 완전히 구성되지 않았다면 클라이언트 생성 건너뛰기
    if not all([settings.KS3_BUCKET, settings.KS3_ACCESS_KEY, settings.KS3_SECRET_KEY, settings.KS3_ENDPOINT]):
        logger.info("KS3 설정이 완전히 구성되지 않았습니다. 업로드가 건너뜁니다.")
        return None

    config = Config(
        s3={"addressing_style": "path" if settings.KS3_FORCE_PATH_STYLE else "virtual"},
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
    )
    session = boto3.session.Session(
        aws_access_key_id=settings.KS3_ACCESS_KEY,
        aws_secret_access_key=settings.KS3_SECRET_KEY,
        region_name=settings.KS3_REGION or "ap-northeast-2",
    )
    return session.client("s3", endpoint_url=settings.KS3_ENDPOINT, config=config)


def _gzip_bytes(raw: bytes) -> bytes:
    """바이트 데이터를 gzip으로 압축합니다."""
    buf = io.BytesIO()
    # mtime=0은 동일 입력에 대해 결정론적 출력을 보장합니다.
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as gz:
        gz.write(raw)
    return buf.getvalue()


def _ungzip_bytes(gzipped_data: bytes) -> bytes:
    """gzip으로 압축된 바이트 데이터를 압축 해제합니다."""
    buf = io.BytesIO(gzipped_data)
    with gzip.GzipFile(fileobj=buf, mode="rb") as gz:
        return gz.read()


def upload_behavior_chunk(chunk: EventChunk):
    """
    단일 이벤트 청크를 직렬화, 압축하여 KS3에 업로드합니다.
    """
    if not settings.ENABLE_KS3:
        logger.debug("KS3 업로드가 비활성화되어 있습니다. 청크 업로드를 건너뜁니다.")
        return

    s3_client = _get_ks3_client()
    if not s3_client:
        return

    try:
        # Pydantic 모델을 JSON 문자열로 직렬화한 후 바이트로 인코딩
        chunk_json_bytes = chunk.model_dump_json().encode('utf-8')
        gzipped_body = _gzip_bytes(chunk_json_bytes)

        # 버킷 내 객체 키(경로) 정의
        key = f"behavior-chunks/{chunk.session_id}/chunk_{chunk.chunk_index}_{chunk.total_chunks}.json.gz"

        s3_client.put_object(
            Bucket=settings.KS3_BUCKET,
            Key=key,
            Body=gzipped_body,
            ContentType="application/json",
            ContentEncoding="gzip",
        )
        logger.info(f"KS3에 청크 업로드 성공: s3://{settings.KS3_BUCKET}/{key}")

    except Exception as e:
        logger.error(f"클라이언트 토큰 {chunk.session_id}에 대한 청크 KS3 업로드 실패: {e}")


def upload_entire_session_behavior(payload: CaptchaVerificationRequest, session_id: str):
    """
    전체 세션의 행동 데이터를 직렬화, 압축하여 KS3에 업로드합니다.
    이 함수는 captcha_tasks.py의 원래 upload_ks3_session에서 수정되었습니다.
    """
    if not settings.ENABLE_KS3:
        logger.debug("KS3 업로드가 비활성화되어 있습니다. 세션 업로드를 건너뜁니다.")
        return (None, None, "KS3 업로드 비활성화됨")

    s3_client = _get_ks3_client()
    if not s3_client:
        return (None, None, "KS3 클라이언트 구성되지 않음")

    try:
        # meta와 events는 이미 딕셔너리/딕셔너리 리스트이므로 model_dump 필요 없음
        meta = payload.meta if payload.meta else {}
        events = payload.events if payload.events else []

        lines = [json.dumps({"type": "meta", **meta}, ensure_ascii=False)]
        for ev in events:
            lines.append(json.dumps(
                {"type": "event", **ev}, ensure_ascii=False))
        body = ("\n".join(lines) + "\n").encode("utf-8")

        gzipped_body = _gzip_bytes(body)

        ts = datetime.now(settings.TIMEZONE).strftime("%Y%m%d-%H%M%S")
        fname = f"{ts}_{session_id}.json.gz"
        prefix = settings.KS3_PREFIX.strip('/')
        key = f"{prefix}/{fname}".strip("/")

        s3_client.put_object(
            Bucket=settings.KS3_BUCKET, Key=key, Body=gzipped_body,
            ContentType="application/json", ContentEncoding="gzip",
        )
        logger.info(f"KS3에 세션 데이터 업로드 성공: s3://{settings.KS3_BUCKET}/{key}")
        return (f"s3://{settings.KS3_BUCKET}/{key}", key, len(gzipped_body))

    except Exception as e:
        logger.error(f"클라이언트 토큰 {session_id}에 대한 세션 데이터 KS3 업로드 실패: {e}")
        return (None, None, f"업로드 오류: {e}")


def download_behavior_chunks(client_token: str) -> List[Dict[str, Any]]:
    """
    주어진 client_token에 대한 모든 행동 청크를 KS3에서 다운로드, 압축 해제 및 병합합니다.
    """
    if not settings.ENABLE_KS3:
        logger.debug("KS3 업로드가 비활성화되어 있습니다. 청크 다운로드를 건너뜁니다.")
        return []

    s3_client = _get_ks3_client()
    if not s3_client:
        return []

    all_events = []
    chunk_prefix = f"behavior-chunks/{client_token}/"

    try:
        response = s3_client.list_objects_v2(
            Bucket=settings.KS3_BUCKET, Prefix=chunk_prefix)
        if "Contents" not in response:
            logger.info(f"클라이언트 토큰 {client_token}에 대한 청크를 찾을 수 없습니다.")
            return []

        # 청크를 올바른 순서로 정렬하기 위해 인덱스 기준으로 정렬
        chunk_keys = sorted([obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".json.gz")],
                            key=lambda k: int(k.split("chunk_")[1].split("_")[0]))

        for key in chunk_keys:
            obj = s3_client.get_object(Bucket=settings.KS3_BUCKET, Key=key)
            gzipped_content = obj["Body"].read()
            decompressed_content = _ungzip_bytes(
                gzipped_content).decode("utf-8")
            chunk_data = json.loads(decompressed_content)

            # chunk_data가 EventChunk 구조라고 가정
            if "events" in chunk_data:
                all_events.extend(chunk_data["events"])
            else:
                logger.info(f"청크 {key}에 'events' 키가 없습니다.")

        logger.info(
            f"클라이언트 토큰 {client_token}에 대해 {len(chunk_keys)}개의 청크를 성공적으로 다운로드하고 병합했습니다.")
        return all_events

    except Exception as e:
        logger.error(f"클라이언트 토큰 {client_token}에 대한 청크 다운로드 또는 병합 실패: {e}")
        return []
