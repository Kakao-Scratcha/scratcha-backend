from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.services.contact_service import ContactService # ContactService 클래스 임포트
from app.schemas.contact import ContactCreate, ContactResponse
from db.session import get_db

router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 문의 등록",
    description="사용자로부터 새로운 문의를 접수합니다. 별도의 인증이 필요하지 않습니다."
)
def createContact(
    *,
    contactIn: ContactCreate,
    db: Session = Depends(get_db) # Direct DB session injection
) -> ContactResponse:
    """
    새로운 문의를 생성하는 API 엔드포인트입니다.
    """
    # 1. ContactService 인스턴스 생성
    contactService = ContactService(db)
    # 2. ContactService를 통해 새로운 문의 생성
    return contactService.createContact(contactIn=contactIn)