# app/repositories/payment_repo.py
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_payment(self, *, payment_in: PaymentCreate) -> Payment:
        """
        새로운 결제 정보를 데이터베이스 세션에 추가합니다.
        이 메서드는 commit을 수행하지 않으므로, 호출 측에서 트랜잭션을 관리해야 합니다.
        """
        # Pydantic 스키마를 SQLAlchemy 모델 인스턴스로 변환합니다.
        db_payment = Payment(**payment_in.dict())
        # 데이터베이스 세션에 모델 인스턴스를 추가합니다. (커밋 X)
        self.db.add(db_payment)
        # 생성된 결제 객체를 반환합니다.
        return db_payment

    def get_payments_by_user_id(self, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Payment]:
        """
        특정 사용자의 결제 내역 리스트를 조회합니다.
        """
        return self.db.query(Payment).options(joinedload(Payment.user)).filter(Payment.userId == user_id).order_by(Payment.createdAt.desc()).offset(skip).limit(limit).all()

    def get_payments_count_by_user_id(self, *, user_id: int) -> int:
        """
        특정 사용자의 전체 결제 내역 수를 조회합니다.
        """
        return self.db.query(Payment).filter(Payment.userId == user_id).count()
