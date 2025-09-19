
from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base
#from .pantry_meal_instructions import PantryMealInstructions

class Pantry(Base):
    __tablename__ = "pantries"
    
    pantry_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    pantry_ingredient_id = Column(Integer, ForeignKey("pantry_ingredients.pantry_ingredient_id"))
    meal_type = Column(String(255))
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    #pantry_ingredients = relationship("PantryIngredient", back_populates="pantry")
    pantry_requests = relationship("PantryRequest", back_populates="pantry")
    pantry_meal_instructions = relationship("PantryMealInstructions", back_populates="pantry")
    pantry_meal_nutrition_info = relationship("PantryMealnutritions", back_populates="pantry")