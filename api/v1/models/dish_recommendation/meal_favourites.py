from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, DateTime, Integer, ForeignKey, String, UniqueConstraint, func, Boolean, Text, Float
from sqlalchemy.orm import relationship
from db.session import Base
#from api.v1.models.user import User

class MealFavourite(Base):
    __tablename__ = "meal_favourites"
    
    meal_favourite_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    meal_id = Column(Integer, ForeignKey("generated_meals.meal_id"))
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="meal_favourites")
    generated_meals = relationship("GeneratedMeals", back_populates="meal_favourites")
    
    

   