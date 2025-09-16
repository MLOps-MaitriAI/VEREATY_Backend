from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base

class MealInstructions(Base):
    __tablename__ = "meal_instructions"
    
    instruction_id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("generated_meals.meal_id"))
    step_number = Column(Integer)
    instruction_text = Column(Text)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    generated_meals = relationship("GeneratedMeals", back_populates="meal_instructions")
    