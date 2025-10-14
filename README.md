# scratCHA - Backend
## 유저의 스크래치 행동 기반 AI 캡챠 SaaS 플랫폼
- 역할
    - 시스템 아키텍처와 ERD 설계, AI 모델의 API 서빙
- 사용 기술
    - 언어
      - Python
    - 프레임워크
        - FastAPI
    - 라이브러리
        - Pydantic, SQLAlchemy, Alembic
    - 데이터베이스
        - MySQL
    - 데브옵스
        - Kakao Cloud VM, GPU, Object Storage, Container Registry
        - Kubernetes
        - Git Actions

## 시스템 아키텍처
![백엔드_아키텍처-시스템아키텍처](https://github.com/user-attachments/assets/2223177e-4f17-48e1-8de0-8ee823c55179)

  
## 배치 서버로 캡챠 문제 생성 일괄 처리
### 문제 확인
<img width="4720" height="1840" alt="image" src="https://github.com/user-attachments/assets/9b45838d-9fe4-416f-b90f-c373fdd7dc56" />

- 기존의 모놀리식 서버
- 캡챠 생성 요청마다 실시간으로 모델이 문제를 생성하여 지연 발생
 
### 개선 사항

<img width="5044" height="3124" alt="image" src="https://github.com/user-attachments/assets/ca14270d-1dbc-4a38-89b4-a3097b725f43" />

- API 서버와 문제 생성 서버(배치)를 생성
- 기존의 로직에서 모델을 분리하고 배치 서버에서 스케줄링하여 일괄적으로 문제 생성
- 매일 1000개의 문제를 생성하여 DB에 저장
- 요청 시 DB에서 랜덤으로 1개의 문제가 제공
- 문제 생성 시간 0초 확보

### 회고
이 사례는 처음에는 비동기를 사용해야 하나 고민했지만, 우리 서비스의 기획상 사용자는 어차피 문제를 확인하고 풀어야 하기에 시간이 걸리더라고 문제는 생성되어야만 했습니다. 그래서 MSA와 같은 접근 방식을 택했고 결과적으로 지연없는 문제 제공을 확인하면서 서비스를 인스턴스 별로 나누어 운영하는 것이 효율적이고 좋은 해결 방안이 될 수 있음을 확인한 사례였습니다.
 
## JSON 전송 시, failed to fetch 에러 발생
### 문제 확인
<img width="2920" height="1040" alt="image" src="https://github.com/user-attachments/assets/79cf3d83-183a-4bd5-983b-58f1596769ec" />

- 클라이언트에서 행동 검증 데이터를 서버로 전송할 때, failed to fetch 에러 발생 확인
- axios의 fetch 시 전송 가능한 용량 제한 (약 29KB)

### 개선 사항
<img width="3160" height="1560" alt="image" src="https://github.com/user-attachments/assets/19fe65c9-bb82-4422-9069-7d3947ad3ea7" />

- 클라이언트에서 JSON 파일을 청크로 n개로 나누어 전송하고 먼저 오브젝트 스토리지에 저장
- 스토리지의 청크로 나뉜 JSON 을 다시 병합하여 행동 데이터 모델의 인풋으로 전달
- 데이터를 보내는 과정에서 지연 발생
- fetch 문제는 해결했으나 행동데이터가 많을수록 청크 사이즈가 많아져 오히려 오브젝트 스토리지로 전송하는 지연이 발생 →약 1초
   
## 비동기 작업 구조
<img width="6652" height="1800" alt="image" src="https://github.com/user-attachments/assets/d1b2765e-e380-46b1-a45a-1b4a47960e1d" />

### 행동검증 결과 데이터 업로드 비동기 처리
- 행동 검증 모델의 지도학습 목적으로 검증 결과 데이터를 저장할 필요가 생김
- 데이터의 저장이 완료되기까지의 지연을 줄이고 계속해서 다음 요청을 처리해야 하기에 도입

### 행동 검증 모델 로직의 비동기 처리
- 실시간적으로 행동 검증 모델을 서빙하는데에 있어 서비스 지연의 우려가 고려되어 워커를 추가로 도입
- 하지만 테스트시에 큰 변화를 확인하진 못함
  → 오히려 클라이언트에서 비동기 작업을 체크하는 요청이 늘어나게 되어 성능적으로 부적절한 구조가 되었기에 현재는 실시간 처리로 변경함

## 문제세션 타임아웃 스케줄링
### 도입 이유
<img width="3360" height="1200" alt="image" src="https://github.com/user-attachments/assets/376cfd0b-3514-4812-a80b-09d246fdf560" />

- 메시지 브로커의 워커로 Celery를 사용중이고 Beat라는 스케줄러를 지원하기에 채택
- 새로고침으로 문제가 새로 생성되거나 네트워크의 오류로 유저가 풀지 못한 캡쳐를 TIMEOUT(3분) 으로 지정하여 세션과 로그의 1:1 트랜잭션을 유지하기 위함
