from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from api.v1.models.pantry.pantry_ingredients import PantryIngredient
from db.session import get_db
from auth.auth_bearer import JWTBearer, get_current_user
from api.v1.models.user.user_auth import User

router = APIRouter()

# Request schema for adding multiple ingredients
class PantryIngredientCreateRequest(BaseModel):
    ingredient_name: str
    quantity: str

class PantryIngredientListRequest(BaseModel):
    ingredients: List[PantryIngredientCreateRequest]

@router.post("/pantry/ingredients", dependencies=[Depends(JWTBearer())])
async def add_multiple_pantry_ingredients(
    ingredient_list: PantryIngredientListRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    added_ingredients = []
    skipped_ingredients = []

    try:
        for ingredient_data in ingredient_list.ingredients:
            # Check for duplicate ingredient for this user
            existing_ingredient = db.query(PantryIngredient).filter_by(
                ingredient_name=ingredient_data.ingredient_name,
                created_by=current_user.user_id
            ).first()

            if existing_ingredient:
                skipped_ingredients.append(ingredient_data.ingredient_name)
                continue  # skip duplicates

            # Create new ingredient
            new_ingredient = PantryIngredient(
                ingredient_name=ingredient_data.ingredient_name,
                quantity=ingredient_data.quantity,
                created_by=current_user.user_id
            )
            db.add(new_ingredient)
            db.flush()  # flush to get ID

            added_ingredients.append({
                "pantry_ingredient_id": new_ingredient.pantry_ingredient_id,
                "ingredient_name": new_ingredient.ingredient_name,
                "quantity": new_ingredient.quantity
            })

        db.commit()

        return {
            "message": "Ingredients processed successfully",
            "added_ingredients": added_ingredients,
            "skipped_ingredients": skipped_ingredients
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding ingredients: {str(e)}")


@router.get("/pantry/ingredients", dependencies=[Depends(JWTBearer())])
async def get_pantry_ingredients(
    ingredient_name: str = Query(None, description="Filter by ingredient name (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        query = db.query(PantryIngredient).filter(
            PantryIngredient.created_by == current_user.user_id
        )

        if ingredient_name:
            query = query.filter(PantryIngredient.ingredient_name.ilike(f"%{ingredient_name}%"))

        ingredients = query.all()

        result = [
            {
                "pantry_ingredient_id": ing.pantry_ingredient_id,
                "ingredient_name": ing.ingredient_name,
                "quantity": ing.quantity,
                "created_at": ing.created_at,
                "updated_at": ing.updated_at
            } for ing in ingredients
        ]

        return {
            "message": f"Found {len(result)} ingredients",
            "ingredients": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ingredients: {str(e)}")
    

# Request schema for updating a pantry ingredient
class PantryIngredientUpdateRequest(BaseModel):
    ingredient_name: str = None
    quantity: str = None

@router.put("/pantry/ingredient/{ingredient_id}", dependencies=[Depends(JWTBearer())])
async def update_pantry_ingredient(
    ingredient_id: int = Path(..., description="ID of the ingredient to update"),
    ingredient_data: PantryIngredientUpdateRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Find the ingredient belonging to the current user
        ingredient = db.query(PantryIngredient).filter(
            PantryIngredient.pantry_ingredient_id == ingredient_id,
            PantryIngredient.created_by == current_user.user_id
        ).first()

        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found or does not belong to the user")

        # Check for duplicate name if updating
        if ingredient_data.ingredient_name and ingredient_data.ingredient_name != ingredient.ingredient_name:
            duplicate = db.query(PantryIngredient).filter(
                PantryIngredient.ingredient_name == ingredient_data.ingredient_name,
                PantryIngredient.created_by == current_user.user_id
            ).first()
            if duplicate:
                raise HTTPException(status_code=400, detail="Ingredient name already exists for this user")

        # Update fields
        if ingredient_data.ingredient_name:
            ingredient.ingredient_name = ingredient_data.ingredient_name
        if ingredient_data.quantity:
            ingredient.quantity = ingredient_data.quantity

        ingredient_data.u

        db.commit()
        db.refresh(ingredient)

        return {
            "message": "Ingredient updated successfully",
            "pantry_ingredient_id": ingredient.pantry_ingredient_id,
            "ingredient_name": ingredient.ingredient_name,
            "quantity": ingredient.quantity
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating ingredient: {str(e)}")
    

@router.delete("/pantry/ingredient/{ingredient_id}", dependencies=[Depends(JWTBearer())])
async def delete_pantry_ingredient(
    ingredient_id: int = Path(..., description="ID of the ingredient to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        ingredient = db.query(PantryIngredient).filter(
            PantryIngredient.pantry_ingredient_id == ingredient_id,
            PantryIngredient.created_by == current_user.user_id
        ).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found or does not belong to the user")

        db.delete(ingredient)
        db.commit()

        return {
            "message": "Ingredient deleted successfully",
            "pantry_ingredient_id": ingredient_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting ingredient: {str(e)}")