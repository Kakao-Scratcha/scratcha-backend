#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import gzip
import io
import argparse
import time
import boto3
import requests
from botocore.config import Config
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import logging

# 로거 설정
logger = logging.getLogger(__name__)
# 기본 핸들러가 없으면 추가 (중복 방지)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)  # Corrected typo here
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # 기본 레벨은 INFO

# --- 설정 --- #
# 사용하실 API 키를 여기에 입력하세요.
API_KEY = "41378b9f15442486b2367e014693986a8ba3b976a8753601aa39dbf56b80d4ac"
# ------------ #

CHUNK_SIZE = 50  # 명세서에 따른 이벤트 청크 크기


def getenv_any(names, default=None):
    """환경 변수 목록에서 가장 먼저 발견되는 값을 반환합니다."""
    for n in names:
        v = os.getenv(n)
        if v is not None and str(v).strip() != "":
            return v
    return default


def load_s3_config():
    """S3 접속에 필요한 환경 변수를 로드하고 딕셔너리로 반환합니다."""
    load_dotenv()
    config = {
        "endpoint_url": getenv_any(["KS3_ENDPOINT", "S3_ENDPOINT_URL"]),
        "region_name": getenv_any(["KS3_REGION", "S3_REGION"], "ap-northeast-2"),
        "bucket_name": "yji-test-bucket",  # 실제 버킷 이름으로 변경 필요
        "access_key": getenv_any(["KS3_ACCESS_KEY", "S3_ACCESS_KEY"]),
        "secret_key": getenv_any(["KS3_SECRET_KEY", "S3_SECRET_KEY"]),
        "force_path_style": getenv_any(["KS3_FORCE_PATH_STYLE", "S3_FORCE_PATH_STYLE"], "1") == "1",
    }
    required_keys = ["endpoint_url", "bucket_name", "access_key", "secret_key"]
    if not all(config[key] for key in required_keys):
        logger.error("S3 설정에 필요한 환경 변수가 누락되었습니다.")
        logger.error(f"필수 항목: {required_keys}")
        sys.exit(1)
    return config


def get_s3_client(config):
    """설정 정보를 바탕으로 S3 클라이언트를 생성합니다."""
    cfg = Config(
        s3={"addressing_style":
            "path" if config["force_path_style"] else "virtual"},
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
    )
    session = boto3.session.Session(
        aws_access_key_id=config["access_key"],
        aws_secret_access_key=config["secret_key"],
        region_name=config["region_name"],
    )
    return session.client("s3", endpoint_url=config["endpoint_url"], config=cfg)


def download_and_parse_session(client, bucket, key):
    """S3에서 세션 파일을 다운로드하고 파싱하여 meta와 events를 추출합니다."""
    try:
        logger.info(f"S3 버킷 '{bucket}'에서 파일 다운로드 중: {key}")
        response = client.get_object(Bucket=bucket, Key=key)
        with gzip.GzipFile(fileobj=io.BytesIO(response["Body"].read()), mode="rb") as gz:
            content = gz.read().decode("utf-8")

        lines = content.strip().split('\n')
        meta, events = None, []
        for line in lines:
            try:
                data = json.loads(line)
                if data.get("type") == "meta":
                    if 'type' in data:
                        del data["type"]
                    meta = data
                elif data.get("type") != "label":
                    # EventData 스키마에 't' 필드가 있는지 확인
                    if "t" not in data and data.get("type") in ["moves", "moves_free"] and "payload" in data and "base_t" in data["payload"]:
                        data["t"] = data["payload"]["base_t"]
                    events.append(data)
            except json.JSONDecodeError:
                logger.info(f"JSON 파싱 실패, 라인 건너뜀: {line}")
                continue

        if not meta:
            logger.error("파일에서 'meta' 정보를 찾을 수 없습니다.")
            return None
        return {"meta": meta, "events": events}
    except client.exceptions.NoSuchKey:
        logger.error(
            f"오류: S3 버킷 '{bucket}'에서 파일 '{key}'를 찾을 수 없습니다.")
        return None
    except Exception as e:
        logger.error(f"파일 다운로드 또는 처리 중 오류 발생: {e}")
        return None


def get_captcha_problem(problem_url, api_key):
    """/captcha/problem API를 호출하여 새로운 캡챠 문제 정보를 받습니다."""
    try:
        logger.info(f"'{problem_url}'에서 새로운 캡챠 문제 요청 중...")
        headers = {"X-Api-Key": api_key}
        response = requests.post(problem_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"/captcha/problem API 호출 실패: {e}")
        logger.error(f"응답: {e.response.text if e.response else 'N/A'}")
        return None
    except KeyError:
        logger.error("/captcha/problem 응답에 필수 필드가 없습니다.")
        logger.error(f"응답: {response.text}")
        return None


def send_event_chunk(
    chunk_url: str,
    client_token: str,
    chunk_events: List[Dict[str, Any]],
    chunk_index: int,
    total_chunks: int,
    meta: Dict[str, Any],
    timestamp: int,
    delay_ms: int = 100  # 명세서에 따른 청크 전송 간격
):
    """/api/events/chunk API를 호출하여 이벤트 청크를 전송합니다."""
    try:
        logger.info(
            f"'{chunk_url}'로 이벤트 청크 {chunk_index+1}/{total_chunks} 전송 중...")
        request_body = {
            "client_token": client_token,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "events": chunk_events,
            "meta": meta,
            "timestamp": timestamp
        }
        # logger.info(f"전송할 청크 데이터: {json.dumps(request_body, indent=2, ensure_ascii=False)}") # 디버깅용
        headers = {"Content-Type": "application/json"}
        response = requests.post(chunk_url, headers=headers, json=request_body)
        response.raise_for_status()
        logger.info(f"청크 {chunk_index+1} 전송 성공: {response.json()}")
        time.sleep(delay_ms / 1000.0)  # 지연 시간 적용
    except requests.exceptions.RequestException as e:
        logger.error(
            f"/api/events/chunk API 호출 실패 (청크 {chunk_index+1}, 클라이언트 토큰: {client_token}): {e}")
        logger.error(f"응답: {e.response.text if e.response else 'N/A'}")
        sys.exit(1)


def submit_for_verification(verify_url, api_key, client_token, answer, behavior_data):
    """/captcha/verify API를 호출하여 검증을 요청합니다."""
    try:
        logger.info(f"'{verify_url}'로 검증 요청 전송 중...")
        headers = {"X-Api-Key": api_key, "X-Client-Token": client_token}
        # 청크로 대부분의 이벤트가 전송되었으므로, verify 요청에는 meta와 빈 events 리스트를 보냅니다.
        request_body = {"answer": answer,
                        "meta": behavior_data["meta"], "events": []}

        response = requests.post(
            verify_url, headers=headers, json=request_body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"/captcha/verify API 호출 실패: {e}")
        logger.error(f"응답: {e.response.text if e.response else 'N/A'}")
        return None


def poll_for_result(result_url_base, task_id, max_retries=30, interval=2):
    """taskId를 사용하여 최종 검증 결과를 폴링합니다."""
    result_url = f"{result_url_base.strip('/')}/{task_id}"
    logger.info(f"'{result_url}'에서 최종 결과 폴링 시작...")
    for i in range(max_retries):
        try:
            response = requests.get(result_url)
            if response.status_code == 200:
                logger.info("검증 성공! 최종 결과를 출력합니다.")
                return response.json()
            elif response.status_code == 202:
                logger.info(".")
                time.sleep(interval)
                continue
            else:
                logger.error(
                    f"결과 조회 실패 (상태 코드: {response.status_code})")
                logger.error(f"응답: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"결과 조회 API 호출 실패: {e}")
            return None
    logger.error("폴링 시간 초과. 작업을 완료하지 못했습니다.")
    return None


def main():
    """메인 실행 함수"""
    # API_KEY가 기본값인지 확인
    if API_KEY == "7c1e6fed6c1fe16713965ecac0c0c130b1e53cdc95fda147c66e3ea7305d00a9":
        logger.error("스크립트 상단의 API_KEY 변수에 실제 API 키를 입력해주세요.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="S3에서 캡챠 세션을 리플레이하고 API로 검증합니다.")
    parser.add_argument(
        "s3_filename", help="다운로드할 S3 파일 이름 (예: 20250908-103308_2c7161evbet.json.gz)")
    parser.add_argument(
        "--type", choices=['human', 'bot'], required=True, help="데이터 타입 (human 또는 bot)")
    parser.add_argument(
        "--problem-url", default="http://localhost:8001/api/captcha/problem", help="캡챠 문제 요청 API의 전체 URL")
    parser.add_argument(
        "--verify-url", default="http://localhost:8001/api/captcha/verify", help="캡챠 검증 요청 API의 전체 URL")
    parser.add_argument(
        "--chunk-url", default="http://localhost:8001/api/events/chunk", help="이벤트 청크 전송 API의 전체 URL")
    parser.add_argument(
        "--result-url-base", default="http://localhost:8001/api/captcha/verify/result", help="캡챠 결과 조회 API의 기본 URL")
    args = parser.parse_args()

    # 1. S3 설정 로드 및 클라이언트 생성
    s3_config = load_s3_config()
    s3_client = get_s3_client(s3_config)

    # 2. 새로운 캡챠 문제 정보 발급
    problem_response = get_captcha_problem(args.problem_url, API_KEY)
    if not problem_response or "clientToken" not in problem_response or "options" not in problem_response:
        logger.error("캡챠 문제 정보를 제대로 받지 못했습니다.")
        sys.exit(1)
    client_token = problem_response["clientToken"]
    options = problem_response["options"]
    if "correctAnswer" in problem_response:
        answer_to_send = problem_response["correctAnswer"]
    else:
        answer_to_send = options[0]  # 첫 번째 옵션을 정답으로 가정 (테스트 환경이 아닐 경우)

    logger.info(f"새로운 Client-Token 발급 성공: {client_token}")
    logger.info(f'문제 프롬프트: {problem_response["prompt"]}')
    logger.info(f'선택지: {options}')
    logger.info(f'전송할 답변: {answer_to_send}')

    # 3. S3에서 행동 데이터 다운로드 및 파싱
    prefix = "human_data" if args.type == 'human' else "bot_data"
    s3_key = f"{prefix}/{args.s3_filename}"
    behavior_data = download_and_parse_session(
        s3_client, s3_config["bucket_name"], s3_key)
    if not behavior_data:
        sys.exit(1)

    logger.info("\n--- 다운로드 및 파싱된 행동 데이터 (meta 및 events) ---")
    # logger.info(json.dumps(behavior_data, indent=2, ensure_ascii=False))
    logger.info("-----------------------------------------------------")

    all_events = behavior_data["events"]
    meta_data = behavior_data["meta"]
    total_events = len(all_events)
    total_chunks = (total_events + CHUNK_SIZE - 1) // CHUNK_SIZE
    current_timestamp = int(time.time() * 1000)  # 현재 타임스탬프 (밀리초)

    logger.info(f"총 {total_events}개의 이벤트, {total_chunks}개의 청크로 분할하여 전송합니다.")

    # 4. 이벤트 청크 전송
    for i in range(total_chunks):
        start_index = i * CHUNK_SIZE
        end_index = min((i + 1) * CHUNK_SIZE, total_events)
        chunk_events = all_events[start_index:end_index]
        send_event_chunk(
            args.chunk_url,
            client_token,
            chunk_events,
            i,
            total_chunks,
            meta_data,
            current_timestamp
        )

    # 5. API로 검증 요청 제출
    final_result = submit_for_verification(
        args.verify_url, API_KEY, client_token, answer_to_send, behavior_data)
    if not final_result or "result" not in final_result:
        logger.error("검증 요청에서 유효한 결과를 받지 못했습니다.")
        sys.exit(1)

    # 6. 최종 결과 출력 (동기 방식이므로 폴링 필요 없음)
    logger.info("검증 성공! 최종 결과를 출력합니다.")
    logger.info(json.dumps(final_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
