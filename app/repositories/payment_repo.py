# app/repositories/payment_repo.py
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate

class PaymentRepository:
    """
    결제 정보(`Payment`) 데이터베이스 작업을 처리하는 리포지토리입니다.
    """
    def __init__(self, db: Session):
        """
        PaymentRepository의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db

    def create_payment(self, *, payment_in: PaymentCreate) -> Payment:
        """
        새로운 결제 정보를 데이터베이스에 생성합니다.

        Args:
            payment_in (PaymentCreate): 생성할 결제 정보 스키마.

        Returns:
            Payment: 데이터베이스에 생성된 결제 객체.
        """
        # 1. Pydantic 스키마를 SQLAlchemy 모델 인스턴스로 변환합니다.
        db_payment = Payment(**payment_in.dict())
        # 2. 데이터베이스 세션에 모델 인스턴스를 추가합니다.
        self.db.add(db_payment)
        # 3. 변경사항을 데이터베이스에 커밋합니다.
        self.db.commit()
        # 4. 데이터베이스로부터 최신 상태의 객체를 리프레시합니다.
        self.db.refresh(db_payment)
        # 5. 생성된 결제 객체를 반환합니다.
        return db_payment

    def get_payments_by_user_id(self, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Payment]:
        """
        특정 사용자의 결제 내역 리스트를 조회합니다.

        Args:
            user_id (int): 조회할 사용자의 ID.
            skip (int): 조회할 때 건너뛸 레코드의 수.
            limit (int): 한 번에 조회할 최대 레코드의 수.

        Returns:
            List[Payment]: 조회된 결제 객체의 리스트.
        """
        return self.db.query(Payment).options(joinedload(Payment.user)).filter(Payment.userId == user_id).order_by(Payment.createdAt.desc()).offset(skip).limit(limit).all()

    def get_payments_count_by_user_id(self, *, user_id: int) -> int:
        """
        특정 사용자의 전체 결제 내역 수를 조회합니다.

        Args:
            user_id (int): 조회할 사용자의 ID.

        Returns:
            int: 전체 결제 내역 수.
        """
        return self.db.query(Payment).filter(Payment.userId == user_id).count()