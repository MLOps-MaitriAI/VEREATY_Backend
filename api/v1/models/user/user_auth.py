
from datetime import datetime
from enum import Enum
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from api.v1.schemas.user import StatusEnum
from api.v1.models.onboarding import onboarding_sessions
from db.session import Base

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("onboarding_sessions.session_id"))
    username = Column(String(255), nullable=True)
    email = Column(String(25), unique=True, nullable=True)
    phone_number = Column(String(15), unique=True)
    status = Column(String(255), nullable=False)
    user_type = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    #meal_favourites = relationship("MealFavourite", back_populates="user")
    meal_favourites = relationship("MealFavourite", back_populates="user")
    meal_history = relationship("MealHistory", back_populates="user")
    meal_requests = relationship("MealRequest", back_populates="user")
    #onboarding_sessions = relationship("OnboardingSession", back_populates="users")
    session = relationship("OnboardingSession", back_populates="users")
    social_auths = relationship("SocialAuth", back_populates="user")
    user_sessions = relationship("UserSession", back_populates="user")
    pantry_requests = relationship("PantryRequest", back_populates="user")
    



class OTP(Base):
    __tablename__ = 'otp'
    otp_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(255), nullable=True)
    purpose = Column(String(30), nullable=True)
    otp_code = Column(String(10), nullable=True)
    status = Column(String(255), nullable=True, default="active")
    attempt_count = Column(Integer, nullable=True)
    is_verified = Column(Boolean, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)

    
