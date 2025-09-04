# --- 스테이지 1: 빌더 스테이지 (의존성 설치) ---
FROM python:3.10-slim-bullseye AS builder

WORKDIR /usr/src/app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential     gcc     libmariadb-dev     pkg-config     && rm -rf /var/lib/apt/lists/*

# requirements.txt를 먼저 복사하여 Docker 캐시를 활용합니다.
COPY requirements.txt .

# Python 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt


# --- 스테이지 2: 최종 이미지 스테이지 (실행 환경) ---
FROM python:3.10-slim-bullseye

WORKDIR /app

# 보안을 위해 non-root 사용자 생성
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# 빌더 스테이지에서 설치한 Python 패키지 및 실행 파일 복사
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 및 Alembic 관련 소스 코드 복사
COPY ./app ./app
COPY ./db ./db
COPY ./alembic.ini .
COPY ./alembic ./alembic
COPY ./logging.ini .

# 파일 소유권을 non-root 사용자로 변경
RUN chown -R appuser:appgroup /app

# non-root 사용자로 전환
USER appuser

# Uvicorn 서버가 리스닝할 포트 노출
EXPOSE 8001

# 컨테이너 시작 시 실행될 기본 명령어
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--log-config", "logging.ini"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--log-config", "logging.ini", "--proxy-headers", "--forwarded-allow-ips", "*"]