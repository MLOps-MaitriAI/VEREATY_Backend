from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()
ENV = os.getenv("ENV", "development")




if ENV == "production":
    SQLALCHEMY_DATABASE_URL1 = os.getenv("PROD_DATABASE_URL")
else:
    SQLALCHEMY_DATABASE_URL1 = os.getenv("DEV_DATABASE_URL")

#SQLALCHEMY_DATABASE_URL1 =os.getenv("DEV_DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL1)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def api_response(status_code, data=None, message: str = None, total: int = 0, count: int = 0):
    response_data = {"data": data, "message": message, "status_code": status_code, "total": total, "count": count}
    filtered_response = {key: value for key, value in response_data.items() if value is not None or 0}
    return filtered_response

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """Direct database session for WebSocket and other manual use"""
    return SessionLocal()





