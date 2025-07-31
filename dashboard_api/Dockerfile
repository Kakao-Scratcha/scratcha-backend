# dashboard_api/Dockerfile

# --- 스테이지 1: 빌더 스테이지 (Python 의존성 설치) ---

# AS builder는 이 스테이지에 builder라는 이름을 부여합니다.
# 름을 붙여두면 나중에 다른 스테이지에서 이 builder 스테이지의 결과물을 참조할 수 있습니다.
FROM python:3.10-slim-bullseye AS builder

# 작업 디렉토리 설정
WORKDIR /app

# PYTHONPATH 환경 변수 설정
ENV PYTHONPATH=/app/dashboard_api/app/dashboard_api/app

# 시스템에 필요한 최소한의 패키지 설치
# 파이썬 패키지와, MySQL 드라이버와 연동하기 위한 파리눅스 시스템 라이브러리를 설치
RUN apt-get update && \
    # 불필요한 추천 패키지 설치 방지합니다.
    apt-get install -y --no-install-recommends \ 
    # 컴파일 도구
    build-essential \
    gcc \
    # MySQL 클라이언트 라이브러리
    libmariadb-dev \
    # 패키지 목록을 캐시한 파일을 삭제하여 이미지 크기를 줄입니다.
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 (캐싱 활용을 위해 먼저 복사)
COPY requirements.txt .

# 가상 환경 생성 및 활성화
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 가상 환경에 의존성 설치
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- 스테이지 2: 최종 이미지 스테이지 (실행 환경) ---
# 최소한의 필수 파일만 포함된 실행 가능한 이미지를 만드는 스테이지입니다.
FROM python:3.10-slim-bullseye

# 작업 디렉토리 설정
WORKDIR /app

# PYTHONPATH 환경 변수 설정
ENV PYTHONPATH=/app/dashboard_api/app/dashboard_api/app

# appuser 사용자 생성 및 권한 설정 (보안 강화)
# 컨테이너를 root 사용자(기본값)로 실행하는 것은 보안상 위험합니다.
# appuser라는 시스템 사용자(로그인 셸이 없는)와 appgroup이라는 그룹을 생성하고, 이후 애플리케이션을 이 appuser로 실행하도록 설정합니다
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# 빌더 스테이지에서 설치된 가상 환경 복사
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Uvicorn 서버가 리스닝할 포트 노출
EXPOSE 8000 

# 컨테이너 시작 시 실행될 기본 명령어
# docker-compose.yml에서 override 됨
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 