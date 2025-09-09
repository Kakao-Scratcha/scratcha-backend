from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.models.contact import Contact
from app.schemas.contact import ContactCreate

# 로거 설정
logger = logging.getLogger(__name__)

class ContactRepo:
    def createContact(self, db: Session, *, contactIn: ContactCreate) -> Contact | None:
        # Pydantic 모델을 SQLAlchemy 모델 인스턴스로 변환
        dbContact = Contact(
            name=contactIn.name,
            email=contactIn.email,
            title=contactIn.title,
            content=contactIn.content
        )
        db.add(dbContact)
        return dbContact


contactRepo = ContactRepo()
