from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base

class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"
    
    session_id = Column(String(255), primary_key=True)
    is_complete = Column(Boolean, default=False)
    ip_address = Column(String(45), nullable=False)
    phone_number = Column(String(15), unique=True, nullable=True)
    expires_at = Column(DateTime(timezone=True))
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # onboarding_requests = relationship("OnboardingRequests", back_populates="onboarding_sessions")
    requests = relationship("OnboardingRequests", back_populates="session", cascade="all, delete-orphan")

    #users = relationship("User", back_populates="onboarding_sessions")
    users = relationship("User", back_populates="session")