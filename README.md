### 유저의 스크래치 행동 기반 AI 캡챠 SaaS 플랫폼
---
- 역할
    - 시스템 아키텍처와 ERD 설계, AI 모델의 API 서빙
- 사용 기술
    - FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic, MySQL, Kakao Cloud VM, GPU, Object Storage, Kubernetes
 
  
### 배치 서버로 캡챠 문제 생성 일괄 처리
---
- **문제 확인**
    <img width="4720" height="1840" alt="image" src="https://github.com/user-attachments/assets/9b45838d-9fe4-416f-b90f-c373fdd7dc56" />
    - 캡챠 생성 요청마다 실시간으로 모델이 문제를 생성하여 지연 발생
 
- **개선 사항**
    <img width="5044" height="3124" alt="image" src="https://github.com/user-attachments/assets/ca14270d-1dbc-4a38-89b4-a3097b725f43" />
    - 모델을 분리하고 스케줄링해서 일괄적으로 문제 생성
    - 매일 1000개의 문제를 생성하여 DB에 저장
    - 요청 시 DB에서 랜덤으로 1개의 문제가 제공
    - 문제 생성 시간 0초 확보
