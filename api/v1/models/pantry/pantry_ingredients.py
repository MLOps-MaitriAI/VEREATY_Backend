from sqlalchemy import Column, DateTime, Integer, ForeignKey, String, func
from sqlalchemy.orm import relationship
from db.session import Base

class PantryIngredient(Base):
    __tablename__ = "pantry_ingredients"

    pantry_ingredient_id = Column(Integer, primary_key=True, autoincrement=True)
    #pantry_id = Column(Integer, ForeignKey("pantries.pantry_id"), nullable=False)
    ingredient_name = Column(String(255), nullable=False)
    quantity=Column(String(255), nullable=False)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # relationship back to Pantry
    #pantry = relationship("Pantry", back_populates="pantry_ingredients")
    