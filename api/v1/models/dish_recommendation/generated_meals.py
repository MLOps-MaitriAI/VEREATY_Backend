from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base


class GeneratedMeals(Base):
    __tablename__ = "generated_meals"
    
    meal_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("meal_requests.user_request_id"))
    meal_name = Column(String(255))
    description = Column(Text)
    prep_time_mins = Column(Integer)
    image_url = Column(String(255))
    ai_confidence_score = Column(Float)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    
    # Relationships
    meal_favourites = relationship("MealFavourite", back_populates="generated_meals")
    meal_history = relationship("MealHistory", back_populates="generated_meal")
    meal_ingredients = relationship("MealIngredient", back_populates="generated_meals")
    meal_instructions = relationship("MealInstructions", back_populates="generated_meals")

    