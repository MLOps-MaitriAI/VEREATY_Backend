import os
import logging
from typing import List, Optional
from datetime import datetime

import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.v1.models.onboarding.onboarding_requests import OnboardingRequests
from api.v1.models.onboarding.onboarding_sessions import OnboardingSession
from api.v1.models.user.user_auth import User
from api.v1.models.pantry.pantry_ingredients import PantryIngredient
from api.v1.models.pantry.pantries import Pantry
from api.v1.models.pantry.pantry_requests import PantryRequest
from api.v1.models.pantry.pantry_generated_meals import PantryGeneratedMeals
from api.v1.models.pantry.pantry_meal_instructions import PantryMealInstructions
from api.v1.models.pantry.pantry_meal_nutrition_info import PantryMealnutritions
from db.session import get_db
from auth.auth_bearer import JWTBearer, get_current_user
from utils.onboarding_function import PreferenceExtractor
from pydantic import BaseModel
from utils.pentry_meals_generate_function import MealImageGenerator, generate_meals_llm

logger = logging.getLogger(__name__)
router = APIRouter()
base_url = os.getenv("Base_url")


# -------------------------------
# Request Schema
# -------------------------------
class GeneratePantryMealsRequest(BaseModel):
    ingredient_id: List[int]
    meal_type: str
    num_dishes: Optional[int] = 3
    days: Optional[int] = 1
    generate_images: Optional[bool] = True


# -------------------------------
# POST Generate Pantry Meals
# -------------------------------
# -------------------------------
# POST Generate Pantry Meals
# -------------------------------
@router.post("/pantry/generated-meals", dependencies=[Depends(JWTBearer())])
async def generate_pantry_meals(
    request_data: GeneratePantryMealsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if request_data.meal_type not in ["breakfast", "lunch", "dinner"]:
            raise HTTPException(status_code=400, detail="Invalid meal_type")

        # Fetch pantry ingredients from DB
        pantry_ingredients = db.query(PantryIngredient).filter(
            PantryIngredient.pantry_ingredient_id.in_(request_data.ingredient_id)
        ).all()
        ingredient_names = [pi.ingredient_name for pi in pantry_ingredients]
        if not ingredient_names:
            raise HTTPException(status_code=400, detail="No pantry ingredients found.")

        # Fetch completed onboarding session
        onboarding_db = db.query(OnboardingSession).filter(
            OnboardingSession.phone_number == current_user.phone_number,
            OnboardingSession.is_complete == True
        ).first()
        if not onboarding_db:
            raise HTTPException(status_code=404, detail="No completed session found.")

        # Fetch conversation history
        existing_responses = db.query(OnboardingRequests).filter_by(
            session_id=onboarding_db.session_id
        ).all()
        if not existing_responses:
            raise HTTPException(status_code=404, detail="No conversation history found")

        conversation = [
            {"question": r.questions, "answer": r.answer, "preference_key": getattr(r, "preference_key", None)}
            for r in existing_responses if r.answer
        ]
        meaningful_answers = [r for r in conversation if r.get("answer") and "please specify" not in r.get("answer", "").lower()]
        if len(meaningful_answers) < 5:
            raise HTTPException(status_code=400, detail="Not enough meaningful answers")

        onboarding_preferences = PreferenceExtractor.extract_preferences(conversation)

        # Generate dishes
        generated_dishes = generate_meals_llm(
            ingredient_names=ingredient_names,
            meal_type=request_data.meal_type,
            num_dishes=request_data.num_dishes,
            preferences=onboarding_preferences,
            generate_images=request_data.generate_images
        )

        description_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        image_generator = MealImageGenerator(description_model)

        saved_meals = []
        request_date = datetime.utcnow()

        for day in generated_dishes:
            for d in day.get("dishes", []):
                meal_name = d.get("name")
                if not meal_name:
                    continue

                # Fetch or create pantry ingredient
                pantry_ingredient = db.query(PantryIngredient).filter_by(
                    ingredient_name=meal_name,
                    created_by=current_user.user_id
                ).first()
                if not pantry_ingredient:
                    pantry_ingredient = PantryIngredient(
                        ingredient_name=meal_name,
                        quantity="1",
                        created_by=current_user.user_id
                    )
                    db.add(pantry_ingredient)
                    db.flush()

                # Fetch or create pantry
                pantry = db.query(Pantry).filter_by(
                    user_id=current_user.user_id,
                    pantry_ingredient_id=pantry_ingredient.pantry_ingredient_id
                ).first()
                if not pantry:
                    pantry = Pantry(
                        user_id=current_user.user_id,
                        pantry_ingredient_id=pantry_ingredient.pantry_ingredient_id,
                        meal_type=request_data.meal_type,
                        created_by=current_user.user_id
                    )
                    db.add(pantry)
                    db.flush()

                # Pantry request
                pantry_request = PantryRequest(
                    user_id=current_user.user_id,
                    pantry_id=pantry.pantry_id,
                    meal_type=request_data.meal_type,
                    request_date=request_date,
                    created_by=current_user.user_id
                )
                db.add(pantry_request)
                db.flush()

                # Generate image
                image_url = ""
                if request_data.generate_images:
                    image_url = await image_generator.generate_meal_image(
                        meal_name=meal_name,
                        description=d.get("description", ""),
                        cuisine_type=request_data.meal_type
                    )

                # Save meal
                calories = 0
                if d.get("nutritional"):
                    for nutrient in d.get("nutritional", []):
                        if nutrient.get("type") == "Calories":
                            try:
                                calories = int(nutrient["amount"].split()[0])
                            except ValueError:
                                calories = 0

                meal = PantryGeneratedMeals(
                    pantry_request_id=pantry_request.pantry_request_id,
                    meal_name=meal_name,
                    description=d.get("description"),
                    prep_time_mins=int(d.get("prep_time", 0)) if d.get("prep_time") else 0,
                    #calories=calories,
                    image_url=image_url,
                    ai_confidence_score=d.get("confidence_score", 0),
                    created_by=current_user.user_id
                )
                db.add(meal)
                db.flush()

                # Save instructions
                for idx, instr in enumerate(d.get("instructions", []), start=1):
                    instruction = PantryMealInstructions(
                        pantry_id=pantry.pantry_id,
                        step_number=instr.get("step_number", idx),
                        instruction_text=instr.get("instruction_text"),
                        created_by=current_user.user_id
                    )
                    db.add(instruction)

                # Save nutrition info
                for nutrient in d.get("nutritional", []):
                    if nutrient.get("type") and nutrient.get("amount"):
                        try:
                            value = float(nutrient["amount"].split()[0])
                        except ValueError:
                            value = 0
                        nutrition = PantryMealnutritions(
                            pantry_id=pantry.pantry_id,
                            nutrient_name=nutrient["type"],
                            unit=nutrient.get("unit", ""),
                            value=value,
                            created_by=current_user.user_id
                        )
                        db.add(nutrition)

                saved_meals.append({
                    "pantry_meal_id": meal.pantry_meal_id,
                    "meal_name": meal.meal_name,
                    "pantry_request_id": pantry_request.pantry_request_id,
                    "image_url": meal.image_url,
                    "confidence_score": meal.ai_confidence_score
                })

        db.commit()
        return {"message": f"{len(saved_meals)} pantry meals generated", "generated_meals": saved_meals}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating pantry meals: {str(e)}")


# --------------------------------------
# GET Pantry Generated Meals
# --------------------------------------
@router.get("/pantry/generated-meals", dependencies=[Depends(JWTBearer())])
async def get_generated_meals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        pantry_requests = db.query(PantryRequest).filter(
            PantryRequest.user_id == current_user.user_id
        ).all()

        if not pantry_requests:
            raise HTTPException(status_code=404, detail="No pantry meal requests found")

        result = []

        for pr in pantry_requests:
            meals = db.query(PantryGeneratedMeals).filter(
                PantryGeneratedMeals.pantry_request_id == pr.pantry_request_id
            ).all()

            for meal in meals:
                # Fetch instructions
                instructions = db.query(PantryMealInstructions).filter(
                    PantryMealInstructions.pantry_id == pr.pantry_id
                ).order_by(PantryMealInstructions.step_number.asc()).all()

                # Fetch nutrition info
                nutrition_info = db.query(PantryMealnutritions).filter(
                    PantryMealnutritions.pantry_id == pr.pantry_id
                ).all()

                result.append({
                    "pantry_meal_id": meal.pantry_meal_id,
                    "meal_name": meal.meal_name,
                    "description": meal.description,
                    "prep_time_mins": meal.prep_time_mins,
                    #"calories": meal.calories,
                    "image_url": f"{base_url}/{meal.image_url}" if meal.image_url else None,
                    "confidence_score": meal.ai_confidence_score,
                    "request_date": pr.request_date,
                    "instructions": [
                        {"step_number": instr.step_number, "instruction_text": instr.instruction_text}
                        for instr in instructions
                    ],
                    "nutrition": [
                        {"nutrient_name": n.nutrient_name, "unit": n.unit, "value": n.value}
                        for n in nutrition_info
                    ]
                })

        return {
            "message": f"{len(result)} generated meals found",
            "generated_meals": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pantry meals: {str(e)}")