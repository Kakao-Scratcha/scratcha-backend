# db/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()


# 데이터베이스 연결 URL 설정
# Docker Compose 환경에서 서비스 이름(db)을 호스트로 사용합니다.
# .env 파일에서 환경 변수를 가져옵니다.
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy 엔진 생성
# pool_pre_ping=True는 연결이 유효한지 확인하여 끊어진 연결 문제 방지에 도움을 줍니다.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 세션 로컬 클래스 생성
# 이 클래스의 인스턴스가 실제 데이터베이스 세션이 됩니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
