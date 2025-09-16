import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import enum


class SocialAuth(Base):
    __tablename__ = "social_auth"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    provider = Column(String(255))
    provider_user_id = Column(String(255))
    access_token =Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    refresh_token = Column(String(255))
    expiry_token = Column(String(255))

    user = relationship("User", back_populates="social_auths")
   


