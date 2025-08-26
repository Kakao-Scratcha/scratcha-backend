import os
import sys
from datetime import datetime, timedelta, date
import random
import enum
import sqlalchemy as sa
import uuid

from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Float, ForeignKey, func, Enum, Boolean
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv


# --- Database Setup (from your project's db/base.py and db/session.py) ---
# This part assumes a similar structure to your project.
# You might need to adjust the DATABASE_URL based on your environment.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()

# --- Enums (from your project's app/models/user.py) ---


class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class UserSubscription(enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# --- Models (simplified for mock data generation) ---


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    email = Column(String)
    passwordHash = Column("password_hash", String)
    userName = Column("user_name", String)
    role = Column(Enum(UserRole), default=UserRole.USER)
    plan = Column("subscription_plan", Enum(
        UserSubscription), default=UserSubscription.FREE)
    token = Column("api_token", Integer, default=1000)
    createdAt = Column("created_at", DateTime, server_default=func.now())


class Application(Base):
    __tablename__ = "application"
    id = Column(Integer, primary_key=True)
    appName = Column("app_name", String)
    userId = Column("user_id", Integer, ForeignKey('user.id'))
    user = relationship("User")


class ApiKey(Base):
    __tablename__ = "api_key"
    id = Column(Integer, primary_key=True)
    key = Column(String)
    appId = Column("application_id", Integer, ForeignKey('application.id'))
    userId = Column("user_id", Integer, ForeignKey('user.id'))
    isActive = Column("is_active", Boolean, default=True)
    application = relationship("Application")


class UsageStats(Base):
    __tablename__ = "usage_stats"
    id = Column(Integer, primary_key=True)
    keyId = Column("api_key_id", Integer, ForeignKey("api_key.id"))
    date = Column(Date)
    captchaTotalRequests = Column("captcha_total_requests", Integer)
    captchaSuccessCount = Column("captcha_success_count", Integer)
    captchaFailCount = Column("captcha_fail_count", Integer)
    captchaTimeoutCount = Column("captcha_timeout_count", Integer)
    totalLatencyMs = Column("total_latency_ms", Integer)
    verificationCount = Column("verification_count", Integer)
    avgResponseTimeMs = Column("avg_response_time_ms", Float)
    created_at = Column(DateTime, server_default=func.now())


class CaptchaLog(Base):
    __tablename__ = "captcha_log"
    id = Column(Integer, primary_key=True)
    keyId = Column("api_key_id", Integer, ForeignKey("api_key.id"))
    sessionId = Column("session_id", Integer)
    ipAddress = Column("ip_address", String)
    userAgent = Column("user_agent", String)
    result = Column(String)  # "success", "fail", "timeout"
    latency_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class CaptchaProblem(Base):
    __tablename__ = "captcha_problem"
    id = Column(Integer, primary_key=True, autoincrement=True)
    imageUrl = Column("image_url", String, nullable=False)
    answer = Column("answer", String(20), nullable=False)
    wrongAnswer1 = Column("wrong_answer_1", String(20), nullable=False)
    wrongAnswer2 = Column("wrong_answer_2", String(20), nullable=False)
    wrongAnswer3 = Column("wrong_answer_3", String(20), nullable=False)
    prompt = Column("prompt", String(255), nullable=False)
    difficulty = Column("difficulty", Integer, nullable=False)
    createdAt = Column("created_at", DateTime, server_default=func.now())
    expiresAt = Column("expires_at", DateTime, nullable=False)


class CaptchaSession(Base):
    __tablename__ = "captcha_session"
    id = Column(Integer, primary_key=True)
    keyId = Column("api_key_id", Integer, ForeignKey("api_key.id"), nullable=False)
    captchaProblemId = Column("captcha_problem_id", Integer, ForeignKey("captcha_problem.id", ondelete="CASCADE"), nullable=False)
    clientToken = Column("client_token", String(100), unique=True, nullable=False)
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())


# --- Data Generation Logic ---

def generate_captcha_problems(session, num_problems=10):
    print(f"Generating {num_problems} CaptchaProblem entries...")
    problems = []
    for i in range(num_problems):
        problem = CaptchaProblem(
            imageUrl=f"https://mock-captcha-images.s3.amazonaws.com/image_{i+1}.png",
            answer=f"answer{i+1}",
            wrongAnswer1=f"wrong1_{i+1}",
            wrongAnswer2=f"wrong2_{i+1}",
            wrongAnswer3=f"wrong3_{i+1}",
            prompt=f"Select the image with answer{i+1}",
            difficulty=random.randint(1, 5),
            expiresAt=datetime.now() + timedelta(days=random.randint(30, 365))
        )
        session.add(problem)
        problems.append(problem)
    session.commit()
    print("CaptchaProblem generation complete.")
    return problems

def generate_captcha_sessions(session, api_keys, captcha_problems, num_sessions_per_key=5, start_date=None, end_date=None):
    print(f"Generating CaptchaSession entries for {len(api_keys)} API keys...")
    sessions = []
    for api_key in api_keys:
        for _ in range(num_sessions_per_key):
            if not captcha_problems:
                print("No captcha problems available to create sessions.")
                break
            
            random_problem = random.choice(captcha_problems)
            if start_date and end_date:
                time_diff = end_date - start_date
                random_seconds = random.randint(0, int(time_diff.total_seconds()))
                created_at = start_date + timedelta(seconds=random_seconds)
            else:
                created_at = datetime.now() - timedelta(minutes=random.randint(1, 60)) # Fallback to original if dates not provided
            session_entry = CaptchaSession(
                keyId=api_key.id,
                captchaProblemId=random_problem.id,
                clientToken=str(uuid.uuid4()),
                createdAt=created_at
            )
            session.add(session_entry)
            sessions.append(session_entry)
    session.commit()
    print("CaptchaSession generation complete.")
    return sessions


def generate_mock_data(session, user_id=1, num_api_keys=5, days_for_captcha_log=2):
    print(
        f"Generating mock data for user_id: {user_id} with {num_api_keys} API keys...")

    # 1. Create Admin User if no users exist
    user = session.query(User).first()
    if not user:
        print("No users found. Creating default admin user.")
        # Placeholder hash for "admin1234". In a real app, use a proper hashing function.
        admin_password_hash = "$2b$12$examplehashforadmin1234.examplehash"
        user = User(
            id=user_id,
            email="admin@admin.com",
            passwordHash=admin_password_hash,
            userName="admin",
            role=UserRole.ADMIN,
            plan=UserSubscription.ENTERPRISE,
            token=10000  # Give admin more tokens
        )
        session.add(user)
        session.commit()  # Commit user first to get ID if auto-generated
    else:
        print(f"Using existing user: {user.email} (ID: {user.id})")

    # 2. Ensure API keys exist for the user
    api_keys = []
    for i in range(num_api_keys):
        app_name = f"MockApp{i+1}"
        app = session.query(Application).filter_by(
            userId=user.id, appName=app_name).first()
        if not app:
            print(f"Creating {app_name} for user {user.id}")
            app = Application(appName=app_name, userId=user.id)
            session.add(app)
            session.flush()  # Flush to get app.id if auto-generated

        api_key_value = str(uuid.uuid4())
        api_key = session.query(ApiKey).filter_by(
            appId=app.id, key=api_key_value).first()
        if not app:
            print(f"Creating {app_name} for user {user.id}")
            app = Application(appName=app_name, userId=user.id)
            session.add(app)
            session.flush()  # Flush to get app.id if auto-generated

        api_key_value = str(uuid.uuid4())
        api_key = session.query(ApiKey).filter_by(
            appId=app.id, key=api_key_value).first()
        if not api_key:
            print(f"Creating {api_key_value} for App {app.appName}")
            api_key = ApiKey(key=api_key_value, appId=app.id,
                             userId=user.id, isActive=True)
            session.add(api_key)
            session.flush()  # Flush to get api_key.id if auto-generated
        api_keys.append(api_key)
    session.commit()  # Commit all new apps and api_keys

    # 3. Generate CaptchaProblems
    captcha_problems = generate_captcha_problems(session)

    # Define date range for captcha related data
    end_log_date = datetime.now()
    start_log_date = end_log_date - timedelta(days=days_for_captcha_log)

    # 4. Generate CaptchaSessions
    captcha_sessions = generate_captcha_sessions(session, api_keys, captcha_problems, num_sessions_per_key=600, start_date=start_log_date, end_date=end_log_date)

    # 5. Generate UsageStats for the last year ---
    print("Generating UsageStats for the last year...")
    today = date.today()
    one_year_ago = today - timedelta(days=365)

    current_date = one_year_ago
    while current_date <= today:
        for api_key in api_keys:
            # Check if data for this date and key already exists
            existing_stat = session.query(UsageStats).filter_by(
                keyId=api_key.id, date=current_date).first()
            if existing_stat:
                continue

            total_requests = random.randint(500, 5000)
            success_ratio = random.uniform(0.85, 0.95)
            timeout_ratio = random.uniform(0.01, 0.05)

            success_count = int(total_requests * success_ratio)
            timeout_count = int(total_requests * timeout_ratio)
            fail_count = total_requests - success_count - timeout_count
            if fail_count < 0:
                fail_count = 0
                success_count = total_requests - timeout_count

            verification_count = total_requests

            if verification_count > 0:
                total_latency_ms = sum(random.randint(100, 500)
                                       for _ in range(verification_count))
                avg_response_time_ms = total_latency_ms / verification_count
            else:
                total_latency_ms = 0
                avg_response_time_ms = 0.0

            stat = UsageStats(
                keyId=api_key.id,
                date=current_date,
                captchaTotalRequests=total_requests,
                captchaSuccessCount=success_count,
                captchaFailCount=fail_count,
                captchaTimeoutCount=timeout_count,
                totalLatencyMs=total_latency_ms,
                verificationCount=verification_count,
                avgResponseTimeMs=avg_response_time_ms,
                created_at=datetime.combine(
                    current_date, datetime.min.time())
            )
            session.add(stat)

        if current_date.day == 1:
            print(
                f"Committing UsageStats for {current_date.strftime('%Y-%m')}")
            session.commit()
        current_date += timedelta(days=1)
    session.commit()
    print("UsageStats generation complete.")

    # 6. Generate CaptchaLog (1:1 with CaptchaSession) ---
    print(f"Generating CaptchaLog entries (1:1 with CaptchaSession)...")
    for captcha_session_entry in captcha_sessions:
        result_choice = random.choices(["success", "fail", "timeout"], weights=[0.9, 0.08, 0.02], k=1)[0]
        latency = random.randint(100, 500)

        # Ensure log created_at is after or equal to session created_at
        log_created_at = captcha_session_entry.createdAt + timedelta(seconds=random.randint(0, 60)) # Slightly after session creation

        log = CaptchaLog(
            keyId=captcha_session_entry.keyId,
            sessionId=captcha_session_entry.id,
            ipAddress=f"192.168.1.{random.randint(1, 254)}",
            userAgent="MockUserAgent/1.0",
            result=result_choice,
            latency_ms=latency,
            created_at=log_created_at
        )
        session.add(log)
    session.commit()
    print("CaptchaLog generation complete (1:1 with CaptchaSession).")
    print("Mock data generation finished successfully!")
    


# --- Main Execution ---
if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        session.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0;")) # Disable FK checks

        # Create tables if they don't exist (for a fresh DB)
        # Base.metadata.create_all(engine) # Uncomment if you want to create tables via this script

        # You can specify user_id and num_api_keys here
        generate_mock_data(session, user_id=1,
                           num_api_keys=5, days_for_captcha_log=365)
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        session.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1;")) # Re-enable FK checks
        session.close()
