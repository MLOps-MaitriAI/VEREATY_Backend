from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from db.session import Base

class PantryIngredient(Base):
    __tablename__ = "pantry_ingredients"

    pantry_ingredient_id = Column(Integer, primary_key=True, autoincrement=True)
    pantry_id = Column(Integer, ForeignKey("pantries.pantry_id"), nullable=False)
    ingredient_name = Column(String(255), nullable=False)
    quantity=Column(String(255), nullable=False)

    # relationship back to Pantry
    pantry = relationship("Pantry", back_populates="pantry_ingredients")