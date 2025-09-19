from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base


class PantryGeneratedMeals(Base):
    __tablename__ = "pantry_generated_meals"
    
    pantry_meal_id = Column(Integer, primary_key=True, autoincrement=True)
    pantry_request_id = Column(Integer, ForeignKey("pantry_requests.pantry_request_id"))
    meal_name = Column(String(255))
    description = Column(Text)
    prep_time_mins = Column(Integer)
    image_url = Column(String(255))
    ai_confidence_score = Column(Float)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pantry_generated_meals = relationship("PantryRequest", back_populates="pantry_requests")
    