from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from api.v1.models.dish_recommendation.generated_meals import GeneratedMeals
from api.v1.models.dish_recommendation.meal_favourites import MealFavourite
from api.v1.models.dish_recommendation.meal_history import MealHistory
from api.v1.models.user.user_auth import User
from auth.auth_bearer import get_current_user
from db.session import get_db
import os
from datetime import datetime, timezone

router = APIRouter()
base_url = os.getenv("Base_url")
UPLOAD_DIR = "static/uploads"

@router.post("/v1/meal-favourites")
def add_meal_favourite(meal_id: int, db: Session = Depends(get_db),  current_user: User = Depends(get_current_user)):
    try:
        user = db.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        meal = db.query(GeneratedMeals).filter(GeneratedMeals.meal_id == meal_id).first()
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found.")
        
        existing_fav = db.query(MealFavourite).filter(
            MealFavourite.user_id == current_user.user_id,
            MealFavourite.meal_id == meal_id
        ).first()
        if existing_fav:
            raise HTTPException(status_code=409, detail="Meal already favourited by this user.")

        new_favourite = MealFavourite(
            user_id=current_user.user_id,
            meal_id=meal_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_favourite)
        db.commit()
        db.refresh(new_favourite)

        return {
            "message": "Meal added to favourites successfully.",
            "meal_favourite_id": new_favourite.meal_favourite_id,
            "user_id": new_favourite.user_id,
            "meal_id": new_favourite.meal_id,
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred while adding favourite. {e}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred while adding favourite. {e}"
        )


@router.get("/v1/meal-favourites")
def get_meal_favourites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        favourites = db.query(MealFavourite).filter(MealFavourite.user_id == current_user.user_id).all()

        if not favourites:
            return {"message": "No favourite meals found.", "favourites": []}
        
        favourite_meals = []
        for fav in favourites:
            meal = db.query(GeneratedMeals).filter(GeneratedMeals.meal_id == fav.meal_id).first()
            if meal:
                image_urls=f"{base_url}/{meal.image_url}"

                favourite_meals.append({
                    "meal_favourite_id": fav.meal_favourite_id,
                    "meal_id": meal.meal_id,
                    "meal_name": meal.meal_name,
                    "description": meal.description,
                    "prep_time_mins": meal.prep_time_mins,
                    "image_url": image_urls,
                    "ai_confidence_score": getattr(meal, "ai_confidence_score", None),
                    "added_at": fav.created_at.isoformat() if fav.created_at else None
                })

        return {"favourites": favourite_meals}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred while fetching favourites. {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred while fetching favourites. {e}"
        )

@router.delete("/v1/meal-favourites/{favourite_id}")
def delete_meal_favourite(favourite_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        fav = db.query(MealFavourite).filter(
            MealFavourite.meal_favourite_id == favourite_id,
            MealFavourite.user_id == current_user.user_id
        ).first()
        if not fav:
            raise HTTPException(status_code=404, detail="Favourite not found.")

        db.delete(fav)
        db.commit()

        return {"message": "Favourite deleted successfully.", "meal_favourite_id": favourite_id}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred while deleting favourite. {e}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred while deleting favourite. {e}"
        )
    
@router.post("/v1/meal_history")
async def add_meal_history(
    meal_id: int,
    is_cooked: bool = False,
    cooked_image: UploadFile | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Verify user exists
        user = db.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        # Verify meal exists
        meal = db.query(GeneratedMeals).filter(GeneratedMeals.meal_id == meal_id).first()
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found.")

        # Handle uploaded image (optional)
        cooked_image_url = None
        if cooked_image:
            file_location = os.path.join(
                UPLOAD_DIR,
                f"{current_user.user_id}_{meal_id}_{cooked_image.filename}"
            )
            with open(file_location, "wb+") as f:
                f.write(await cooked_image.read())
            cooked_image_url = file_location

        new_entry = MealHistory(
            user_id=current_user.user_id,
            meal_id=meal_id,
            is_cooked=is_cooked,
            cooked_image_url=cooked_image_url,
            created_at=datetime.now(timezone.utc)
        )

        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        return {
            "message": "Meal history added successfully.",
            "meal_history_id": new_entry.meal_history_id,
            "user_id": new_entry.user_id,
            "meal_id": new_entry.meal_id,
            "is_cooked": new_entry.is_cooked,
            "cooked_image_url": new_entry.cooked_image_url
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {e}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred: {e}"
        )