# app/celery_app.py

from celery import Celery
from app.core.config import settings

# Celery 애플리케이션 인스턴스를 생성합니다.
# 첫 번째 인자는 현재 모듈의 이름이며, Celery가 작업을 자동으로 찾을 수 있도록 돕습니다.
celery_app = Celery(
    "worker",
    # 메시지 브로커(RabbitMQ)의 접속 URL을 설정 파일에서 가져옵니다.
    broker=settings.CELERY_BROKER_URL,
    # 작업 결과 저장을 위한 백엔드(RPC)를 설정합니다. 
    # RPC 백엔드는 결과를 AMQP 메시지로 보내는 임시 큐를 사용합니다.
    backend=settings.CELERY_RESULT_BACKEND,
    # Celery 워커가 시작될 때 자동으로 임포트할 작업 모듈 목록을 지정합니다.
    # 여기에 등록된 모듈에서 @celery_app.task 데코레이터가 붙은 함수들을 찾아 작업으로 등록합니다.
    include=["app.tasks.captcha_tasks"],  
)

# Celery 추가 설정
celery_app.conf.update(
    # 작업이 워커에 의해 실행 시작될 때 상태를 'STARTED'로 보고하도록 설정합니다.
    task_track_started=True,
)

# Celery Beat를 사용한 주기적 작업 스케줄을 정의합니다.
celery_app.conf.beat_schedule = {
    # 스케줄 항목의 고유한 이름입니다.
    'cleanup-expired-sessions-every-minute': {
        # 실행할 작업의 전체 경로를 지정합니다. (모듈 경로 + 함수 이름)
        'task': 'app.tasks.captcha_tasks.cleanupExpiredSessionsTask',
        # 실행 주기를 초 단위로 설정합니다. (60.0초 = 1분)
        'schedule': 60.0,  
    },
}