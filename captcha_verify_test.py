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

# --- 설정 --- #
# 사용하실 API 키를 여기에 입력하세요.
API_KEY = "7c1e6fed6c1fe16713965ecac0c0c130b1e53cdc95fda147c66e3ea7305d00a9"
# ------------ #


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
        # "bucket_name": getenv_any(["KS3_BUCKET", "S3_BUCKET"]),
        "bucket_name": "yji-test-bucket",
        "access_key": getenv_any(["KS3_ACCESS_KEY", "S3_ACCESS_KEY"]),
        "secret_key": getenv_any(["KS3_SECRET_KEY", "S3_SECRET_KEY"]),
        "force_path_style": getenv_any(["KS3_FORCE_PATH_STYLE", "S3_FORCE_PATH_STYLE"], "1") == "1",
    }
    required_keys = ["endpoint_url", "bucket_name", "access_key", "secret_key"]
    if not all(config[key] for key in required_keys):
        print("오류: S3 설정에 필요한 환경 변수가 누락되었습니다.", file=sys.stderr)
        print(f"필수 항목: {required_keys}", file=sys.stderr)
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
        print(f"S3 버킷 '{bucket}'에서 파일 다운로드 중: {key}", file=sys.stderr)
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
                    events.append(data)
            except json.JSONDecodeError:
                print(f"경고: JSON 파싱 실패, 라인 건너뜀: {line}", file=sys.stderr)
                continue

        if not meta:
            print("오류: 파일에서 'meta' 정보를 찾을 수 없습니다.", file=sys.stderr)
            return None
        return {"meta": meta, "events": events}
    except client.exceptions.NoSuchKey:
        print(
            f"오류: S3 버킷 '{bucket}'에서 파일 '{key}'를 찾을 수 없습니다.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"파일 다운로드 또는 처리 중 오류 발생: {e}", file=sys.stderr)
        return None


def get_new_client_token(problem_url, api_key):
    """/captcha/problem API를 호출하여 새로운 clientToken을 받습니다."""
    try:
        print(f"'{problem_url}'에서 새로운 캡챠 문제 요청 중...", file=sys.stderr)
        headers = {"X-Api-Key": api_key}
        response = requests.post(problem_url, headers=headers)
        response.raise_for_status()
        return response.json()["clientToken"]
    except requests.exceptions.RequestException as e:
        print(f"오류: /captcha/problem API 호출 실패: {e}", file=sys.stderr)
        print(f"응답: {e.response.text if e.response else 'N/A'}",
              file=sys.stderr)
        return None
    except KeyError:
        print("오류: /captcha/problem 응답에 'clientToken'이 없습니다.", file=sys.stderr)
        print(f"응답: {response.text}", file=sys.stderr)
        return None


def submit_for_verification(verify_url, api_key, client_token, behavior_data):
    """/captcha/verify API를 호출하여 검증을 요청합니다."""
    try:
        print(f"'{verify_url}'로 검증 요청 전송 중...", file=sys.stderr)
        headers = {"X-Api-Key": api_key, "X-Client-Token": client_token}
        request_body = {"answer": "replay_test", **behavior_data}

        response = requests.post(
            verify_url, headers=headers, json=request_body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"오류: /captcha/verify API 호출 실패: {e}", file=sys.stderr)
        print(f"응답: {e.response.text if e.response else 'N/A'}",
              file=sys.stderr)
        return None


def poll_for_result(result_url_base, task_id, max_retries=30, interval=2):
    """taskId를 사용하여 최종 검증 결과를 폴링합니다."""
    result_url = f"{result_url_base.strip('/')}/{task_id}"
    print(f"'{result_url}'에서 최종 결과 폴링 시작...",
          end="", flush=True, file=sys.stderr)
    for i in range(max_retries):
        try:
            response = requests.get(result_url)
            if response.status_code == 200:
                print("\n검증 성공! 최종 결과를 출력합니다.", file=sys.stderr)
                return response.json()
            elif response.status_code == 202:
                print(".", end="", flush=True, file=sys.stderr)
                time.sleep(interval)
                continue
            else:
                print(
                    f"\n오류: 결과 조회 실패 (상태 코드: {response.status_code})", file=sys.stderr)
                print(f"응답: {response.text}", file=sys.stderr)
                return None
        except requests.exceptions.RequestException as e:
            print(f"\n오류: 결과 조회 API 호출 실패: {e}", file=sys.stderr)
            return None
    print("\n오류: 폴링 시간 초과. 작업을 완료하지 못했습니다.", file=sys.stderr)
    return None


def main():
    """메인 실행 함수"""
    if API_KEY == "여기에_API_키를_입력하세요":
        print("오류: 스크립트 상단의 API_KEY 변수에 실제 API 키를 입력해주세요.", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="S3에서 캡챠 세션을 리플레이하고 API로 검증합니다.")
    parser.add_argument(
        "s3_filename", help="다운로드할 S3 파일 이름 (예: 20250908-092649_yaz5q1pdlm.json.gz)")
    parser.add_argument(
        "--type", choices=['human', 'bot'], required=True, help="데이터 타입 (human 또는 bot)")
    parser.add_argument(
        "--problem-url", default="http://localhost:8001/api/captcha/problem", help="캡챠 문제 요청 API의 전체 URL")
    parser.add_argument(
        "--verify-url", default="http://localhost:8001/api/captcha/verify", help="캡챠 검증 요청 API의 전체 URL")
    parser.add_argument(
        "--result-url-base", default="http://localhost:8001/api/captcha/verify/result", help="캡챠 결과 조회 API의 기본 URL")
    args = parser.parse_args()

    # 1. S3 설정 로드 및 클라이언트 생성
    s3_config = load_s3_config()
    s3_client = get_s3_client(s3_config)

    # 2. 새로운 clientToken 발급
    client_token = get_new_client_token(args.problem_url, API_KEY)
    if not client_token:
        sys.exit(1)
    print(f"새로운 Client-Token 발급 성공: {client_token}", file=sys.stderr)

    # 3. S3에서 행동 데이터 다운로드 및 파싱
    prefix = "human_data" if args.type == 'human' else "bot_data"
    s3_key = f"{prefix}/{args.s3_filename}"
    behavior_data = download_and_parse_session(
        s3_client, s3_config["bucket_name"], s3_key)
    if not behavior_data:
        sys.exit(1)

    # 4. API로 검증 요청 제출
    initial_response = submit_for_verification(
        args.verify_url, API_KEY, client_token, behavior_data)
    if not initial_response or "taskId" not in initial_response:
        print("오류: 검증 요청에서 taskId를 받지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    task_id = initial_response["taskId"]
    print(f"검증 작업 접수 성공. Task ID: {task_id}", file=sys.stderr)

    # 5. 최종 결과 폴링
    final_result = poll_for_result(args.result_url_base, task_id)

    if final_result:
        print(json.dumps(final_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
