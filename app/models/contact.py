from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from db.base import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        comment="문의 ID"
    )
    name = Column(
        "name",
        String(50),
        nullable=False,
        comment="작성자 이름"
    )
    email = Column(
        "email",
        String(100),
        nullable=False,
        comment="작성자 이메일"
    )
    title = Column(
        "title",
        String(200),
        nullable=False,
        comment="문의 제목"
    )
    content = Column(
        "content",
        Text,
        nullable=False,
        comment="문의 내용"
    )
    createdAt = Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        comment="생성 시각"
    )
