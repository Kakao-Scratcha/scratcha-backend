from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.contact_repo import contactRepo
from app.schemas.contact import ContactCreate
from app.models.contact import Contact


class ContactService:
    def createContact(self, db: Session, *, contactIn: ContactCreate) -> Contact:
        """
        새로운 문의를 생성하고, 실패 시 HTTP 예외를 발생시킵니다.
        """
        try:
            contact = contactRepo.createContact(db=db, contactIn=contactIn)

            if not contact:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="문의를 등록하는 중 서버에 오류가 발생했습니다."
                )

            db.commit()
            db.refresh(contact)

            # 필요시 이곳에 이메일 발송과 같은 추가적인 비즈니스 로직을 구현할 수 있습니다.
            return contact
        except Exception as e:
            db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"문의 등록 중 오류 발생: {e}"
            )


contactService = ContactService()
