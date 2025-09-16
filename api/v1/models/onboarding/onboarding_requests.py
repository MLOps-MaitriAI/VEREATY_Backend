from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base

class OnboardingRequests(Base):
    __tablename__ = "onboarding_requests"
    
    request_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("onboarding_sessions.session_id"))
    questions = Column(String(255))
    answer = Column(String(255))
    preference_key = Column(String(255), nullable=True)
    options = Column(String(255), nullable=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


    #onboarding_sessions = relationship("OnboardingSession", back_populates="onboarding_requests")
    session = relationship("OnboardingSession", back_populates="requests")
    
