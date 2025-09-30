### 유저의 스크래치 행동 기반 AI 캡챠 SaaS 플랫폼
---
- 역할
    - 시스템 아키텍처와 ERD 설계, AI 모델의 API 서빙
- 사용 기술
    - FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic, MySQL, Kakao Cloud VM, GPU, Object Storage, Kubernetes
 
  
### 배치 서버로 캡챠 문제 생성 일괄 처리
---
- **문제 확인**
    
  ![image.png](attachment:5112fbb2-04db-46a0-9f1b-014aeebfb67b:image.png)
    
  - 캡챠 생성 요청마다 실시간으로 모델이 문제를 생성하여 지연 발생
 
- **개선 사항**
  
  ![image.png](attachment:9ecd3be1-0925-4766-8453-a1dfeaf70686:image.png)
  
  - 모델을 분리하고 스케줄링해서 일괄적으로 문제 생성 → 매일 1000개의 문제를 생성하여 DB에 저장
  - 요청 시 DB에서 랜덤으로 1개의 문제가 제공
  - 문제 생성 시간 0초 확보
