# app/services/event_service.py

import logging
from app.schemas.event import EventChunk
from app.core.ks3 import upload_behavior_chunk
from typing import Dict, Any
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool # Added import

logger = logging.getLogger(__name__)

class EventService:
    """사용자 행동 이벤트 청크를 처리하는 서비스 클래스입니다."""
    def __init__(self):
        pass

    async def process_event_chunk(self, chunk: EventChunk) -> Dict[str, Any]:
        """
        수신된 이벤트 청크를 처리하고 KS3에 업로드합니다.

        Args:
            chunk (EventChunk): 처리할 이벤트 청크 데이터.

        Returns:
            Dict[str, Any]: 청크 처리 결과 메시지.
        """
        logger.info(f"세션 {chunk.client_token}의 청크 {chunk.chunk_index}/{chunk.total_chunks} 수신. 이벤트 수: {len(chunk.events)}")

        try:
            # KS3에 청크 업로드
            await run_in_threadpool(upload_behavior_chunk, chunk) # Wrapped with run_in_threadpool
            logger.info(f"세션 {chunk.client_token}의 청크 {chunk.chunk_index} KS3 업로드 성공.")
        except Exception as e:
            logger.error(f"세션 {chunk.client_token}의 청크 {chunk.chunk_index} KS3 업로드 중 오류 발생: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"이벤트 청크 처리 중 서버 오류가 발생했습니다: {e}"
            )

        return {
            "status": "success",
            "chunk_index": chunk.chunk_index,
            "received_events": len(chunk.events),
            "message": f"청크 {chunk.chunk_index} 수신 완료"
        }