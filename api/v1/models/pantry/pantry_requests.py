
from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base


class PantryRequest(Base):
    __tablename__ = "pantry_requests"
    
    pantry_request_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    pantry_id = Column(Integer, ForeignKey("pantries.pantry_id"))
    request_date = Column(DateTime)
    meal_type = Column(String(255))
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="pantry_requests")
    pantry = relationship("Pantry", back_populates="pantry_requests")