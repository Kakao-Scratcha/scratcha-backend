from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.models.contact import Contact
from app.schemas.contact import ContactCreate

# 로거 설정
logger = logging.getLogger(__name__)

class ContactRepo:
    def createContact(self, db: Session, *, contactIn: ContactCreate) -> Contact | None:
        try:
            # Pydantic 모델을 SQLAlchemy 모델 인스턴스로 변환
            dbContact = Contact(
                name=contactIn.name,
                email=contactIn.email,
                title=contactIn.title,
                content=contactIn.content
            )
            db.add(dbContact)
            db.commit()
            db.refresh(dbContact)
            return dbContact
        except SQLAlchemyError as e:
            logger.error(f"문의 등록 중 데이터베이스 오류 발생: {e}")
            db.rollback()  # 오류 발생 시 트랜잭션 롤백
            return None


contactRepo = ContactRepo()
