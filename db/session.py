# db/session.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

from app.core.config import settings


# 데이터베이스 연결 URL 설정
# Docker Compose 환경에서 서비스 이름(db)을 호스트로 사용합니다.
# .env 파일에서 환경 변수를 가져옵니다.
DATABASE_URL = settings.DATABASE_URL

# SQLAlchemy 엔진 생성
# pool_pre_ping=True는 연결이 유효한지 확인하여 끊어진 연결 문제 방지에 도움을 줍니다.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 세션 로컬 클래스 생성
# 이 클래스의 인스턴스가 실제 데이터베이스 세션이 됩니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    SQLAlchemy 세션을 생성하고, 요청이 끝나면 안전하게 반환합니다.
    FastAPI Depends(get_db)로 사용.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
