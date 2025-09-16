# app/routers/events_router.py

from fastapi import APIRouter, status
from app.schemas.event import EventChunk
from app.services.event_service import EventService
from typing import Dict, Any

# API 라우터 객체 생성
router = APIRouter(
    prefix="/events",
    tags=["Events"],
    responses={404: {"description": "Not found"}},
)

@router.post(
    "/chunk",
    status_code=status.HTTP_200_OK,
    summary="이벤트 청크 전송",
    description="SDK로부터 사용자 행동 이벤트 청크를 수신합니다."
)
async def receive_event_chunk(chunk: EventChunk) -> Dict[str, Any]:
    """
    사용자 행동 이벤트 데이터 청크를 받아 처리합니다.
    수신된 청크는 KS3에 저장됩니다.

    Args:
        chunk (EventChunk): 이벤트 청크 데이터.

    Returns:
        Dict[str, Any]: 처리 결과.
    """
    event_service = EventService()
    result = event_service.process_event_chunk(chunk)
    return result