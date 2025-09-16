# app/schemas/event.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class EventData(BaseModel):
    """단일 사용자 행동 이벤트 데이터를 정의합니다."""
    t: Optional[int] = Field(None, description="상대 타임스탬프 (밀리초)")
    type: str = Field(..., description="이벤트 타입 (예: pointerdown, moves, click)")
    x_raw: Optional[float] = Field(None, description="원본 X 좌표 (픽셀)")
    y_raw: Optional[float] = Field(None, description="원본 Y 좌표 (픽셀)")
    target_role: Optional[str] = Field(
        None, description="클릭 대상 역할 (예: answer-1, canvas-container)")
    target_answer: Optional[str] = Field(
        None, description="클릭 대상 답안 (예: A, B, C, D)")
    payload: Optional[Dict[str, Any]] = Field(
        None, description="추가 데이터 (예: moves 타입에서 사용되는 dts, xrs, yrs)")


class EventChunk(BaseModel):
    """여러 사용자 행동 이벤트 데이터를 포함하는 청크 단위를 정의합니다."""
    session_id: str = Field(..., description="세션의 고유 ID")
    chunk_index: int = Field(..., description="현재 청크의 인덱스 (0부터 시작)")
    total_chunks: int = Field(..., description="전체 청크의 수")
    events: List[EventData] = Field(..., description="이벤트 데이터 목록")
    meta: Dict[str, Any] = Field(...,
                                 description="이벤트 메타 정보 (예: device, viewport)")
    timestamp: int = Field(..., description="청크가 생성된 타임스탬프 (밀리초)")
