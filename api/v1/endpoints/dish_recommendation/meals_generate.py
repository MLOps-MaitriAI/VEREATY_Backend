from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from api.v1.models.dish_recommendation.generated_meals import GeneratedMeals
from api.v1.models.dish_recommendation.meal_ingredients import MealIngredient
from api.v1.models.dish_recommendation.meal_instructions import MealInstructions
from api.v1.models.dish_recommendation.meal_nutrition_info import MealNutritionInfo
from api.v1.models.dish_recommendation.meal_requests import MealRequest
from api.v1.models.user.user_auth import User
from db.session import get_db
from api.v1.models.onboarding.onboarding_sessions import OnboardingSession
from api.v1.models.onboarding.onboarding_requests import OnboardingRequests
from utils.helper_function import get_pagination
from utils.onboarding_function import PreferenceExtractor
from utils.meals_generate_function import extract_time_minutes, get_dish_recommendations
import os

router = APIRouter()

now = datetime.now(timezone.utc)
base_url = os.getenv("Base_url")

@router.post("/generate-meals")
async def generate_meals(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    meals: str = "breakfast,lunch,dinner",
    dishes_per_meal: int = 3,
    start_date: str = Query(default=datetime.today().strftime("%Y-%m-%d"),description="Start date in YYYY-MM-DD format (defaults to today)"),
    num_days: int = Query(1, description="Number of days to generate meal plans for")):
    
    try:
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400,etail="Invalid start_date format. Use YYYY-MM-DD") ##

        if num_days < 1:
            raise HTTPException(status_code=400,detail="num_days must be at least 1")

        ip_address = request.client.host

        session = db.query(OnboardingSession).filter_by(ip_address=ip_address, is_complete=True).first()

        if not session:
            raise HTTPException(status_code=404,detail="No completed session found for this IP")
        
        user_db = db.query(User).filter(User.session_id == session.session_id).first()
        if not user_db:
            raise HTTPException(status_code=404, detail="Complete onboarding first before meal generation")

        existing_responses = (db.query(OnboardingRequests).filter_by(session_id=session.session_id).all())

        if not existing_responses:
            raise HTTPException(status_code=404,detail="No conversation history found")

        conversation = [
            {
                "question": r.questions,
                "answer": r.answer,
                "preference_key": getattr(r, "preference_key", None)
            }
            for r in existing_responses if r.answer
        ]

        meaningful_answers = [
            r for r in conversation
            if r.get("answer") and "please specify" not in r.get("answer", "").lower()
        ]
        if len(meaningful_answers) < 5:
            raise HTTPException(status_code=400,detail="Not enough meaningful answers to generate meals")

        preferences = PreferenceExtractor.extract_preferences(conversation)

        meal_types = [m.strip().lower() for m in meals.split(",") if m.strip()]

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500,detail="Gemini API key missing")

        meal_plan_by_day = {}
        all_generated_dishes = set()
        saved_meals_summary = []

        
        try:
            for day_offset in range(num_days):
                day_date = start_dt + timedelta(days=day_offset)

                recommendations = await get_dish_recommendations(
                    preferences=preferences,
                    meal_types=meal_types,
                    dishes_per_meal=dishes_per_meal,
                    api_key=api_key,
                    exclude_dishes=list(all_generated_dishes)
                )
                unique_recommendations = {}
                for meal_type, dishes in recommendations.items():
                    unique_dishes = []
                    for dish in dishes:
                        if dish["name"] not in all_generated_dishes:
                            unique_dishes.append(dish)
                            all_generated_dishes.add(dish["name"])
                    unique_recommendations[meal_type] = unique_dishes

              
                formatted_date = day_date.strftime("%d-%m-%y")  
                day_name = day_date.strftime("%A")  

                meal_plan_by_day[formatted_date] = {
                    "day_name": day_name,
                    "recommendations": unique_recommendations
                }

                for meal_type, dishes in unique_recommendations.items():
                    for dish in dishes:
                        try:
                            meal_request = MealRequest(
                                user_id=user_db.user_id,  
                                meal_date=day_date,
                                day_name=day_name,
                                meal_type=meal_type,
                               created_at=now
                            )
                            db.add(meal_request)
                            db.flush()  

                            generated_meal = GeneratedMeals(
                                request_id=meal_request.user_request_id,
                                meal_name=dish.get("name"),
                                description=dish.get("description"),
                                prep_time_mins=extract_time_minutes(dish.get("prep_time", "0")),
                                image_url=dish.get("image_url"),  
                                ai_confidence_score=dish.get("confidence_score"),
                                created_at=now
                               
                            )
                            db.add(generated_meal)
                            db.flush()  

                            if dish.get("main_ingredients"):
                                for ingredient in dish["main_ingredients"]:
                                    meal_ingredient = MealIngredient(
                                        meal_id=generated_meal.meal_id,
                                        ingredient_name=ingredient,
                                        quantity="As needed",  
                                        created_at=now
                                    )
                                    db.add(meal_ingredient)
                                    db.flush() 

                            if dish.get("recipe"):
                                for step_num, instruction in enumerate(dish["recipe"], 1):
                                    instruction_text = instruction
                                    if instruction.startswith(f"Step {step_num}:"):
                                        instruction_text = instruction.replace(f"Step {step_num}:", "").strip()

                                    meal_instruction = MealInstructions(
                                        meal_id=generated_meal.meal_id,
                                        step_number=step_num,
                                        instruction_text=instruction_text,
                                        created_at=now
                                    )
                                    db.add(meal_instruction)
                                    db.flush() 

                            if dish.get("nutritional"):
                                for nutrient in dish["nutritional"]:
                                    amount_str = nutrient.get("amount", "0")
                                    value_str = ''.join(filter(lambda x: x.isdigit() or x == '.', amount_str))
                                    value = float(value_str) if value_str else 0.0
                                    
                                    unit = ''.join(filter(str.isalpha, amount_str)) or "unit"

                                    meal_nutrition = MealNutritionInfo(
                                        meal_id=generated_meal.meal_id,
                                        nutrient_name=nutrient.get("name"),
                                        unit=unit,
                                        value=value,
                                        created_at=now
                                    )
                                    db.add(meal_nutrition)

                            saved_meals_summary.append({
                                "meal_id": generated_meal.meal_id,
                                "name": dish.get("name"),
                                "meal_type": meal_type,
                                "date": formatted_date
                            })

                        except Exception as meal_save_error:
                            print(f"Error saving meal {dish.get('name')}: {meal_save_error}")
                            continue

            db.commit()

            meals_by_type = {}
            for meal in saved_meals_summary:
                meal_type = meal["meal_type"]
                meals_by_type[meal_type] = meals_by_type.get(meal_type, 0) + 1

            return {
                "ip_address": ip_address,
                "session_id": session.session_id,
                "preferences": preferences,
                "meal_plan": meal_plan_by_day,
                "database_summary": {
                    "total_meals_saved": len(saved_meals_summary),
                    "meals_by_type": meals_by_type,
                    "saved_meals": saved_meals_summary
                },
                "message": f"Meal recommendations generated and saved successfully for {num_days} day(s)"
            }

        except Exception as db_error:
            db.rollback()
            print(f"Database error: {db_error}")
            
            return {
                "ip_address": ip_address,
                "session_id": session.session_id,
                "preferences": preferences,
                "meal_plan": meal_plan_by_day,
                "database_summary": {
                    "error": "Database save failed, but meal plan generated successfully",
                    "total_meals_saved": 0
                },
                "message": f"Meal recommendations generated for {num_days} day(s). Database save failed: {str(db_error)}"
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Meal generation error: {str(e)}")

@router.get("/generated-meals")
async def get_saved_meals(
    request: Request,
    db: Session = Depends(get_db),
    meal_date: str = Query(None, description="Filter by date (YYYY-MM-DD)"),
    meal_type: str = Query(None, description="Filter by meal type"),
    limit: int = Query(50, description="Maximum number of meals to return"),
    offset: int = Query(0, description="Number of meals to skip")
):
    
    try:
        ip_address = request.client.host
    
        session = db.query(OnboardingSession).filter_by(ip_address=ip_address, is_complete=True).first()

        if not session:
            raise HTTPException(status_code=404,detail="No completed session found for this IP")

        query = (
            db.query(GeneratedMeals)
            .join(MealRequest, GeneratedMeals.request_id == MealRequest.user_request_id)
        )

        if meal_date:
            try:
                filter_date = datetime.strptime(meal_date, "%Y-%m-%d")
                query = query.filter(MealRequest.meal_date == filter_date)
            except ValueError:
                raise HTTPException(status_code=400,detail="Invalid meal_date format. Use YYYY-MM-DD")

        if meal_type:
            query = query.filter(MealRequest.meal_type == meal_type.lower())

        total_count = query.count()
        meals = query.offset(offset).limit(limit).all()

        formatted_meals = []
        for meal in meals:
            ingredients = db.query(MealIngredient).filter_by(meal_id=meal.meal_id).all()
            instructions = (db.query(MealInstructions).filter_by(meal_id=meal.meal_id).order_by(MealInstructions.step_number).all())
            nutrition = db.query(MealNutritionInfo).filter_by(meal_id=meal.meal_id).all()
            meal_request = db.query(MealRequest).filter_by(user_request_id=meal.request_id).first()

            image_url=f"{base_url}/{meal.image_url}"

            formatted_meal = {
                "meal_id": meal.meal_id,
                "name": meal.meal_name,
                "description": meal.description,
                "prep_time_mins": meal.prep_time_mins,
                "ai_confidence_score": meal.ai_confidence_score,
                "meal_type": meal_request.meal_type if meal_request else None,
                "meal_date": meal_request.meal_date.strftime("%Y-%m-%d") if meal_request and meal_request.meal_date else None,
                "day_name":meal_request.day_name,
                "image_url":image_url,
                "ingredients": [
                    {
                        "name": ing.ingredient_name,
                        "quantity": ing.quantity
                    } for ing in ingredients
                ],
                "instructions": [
                    {
                        "step": inst.step_number,
                        "instruction": inst.instruction_text
                    } for inst in instructions
                ],
                "nutrition": [
                    {
                        "nutrient": nut.nutrient_name,
                        "value": nut.value,
                        "unit": nut.unit
                    } for nut in nutrition
                ],
                "created_at": meal.created_at.isoformat()
            }
            formatted_meals.append(formatted_meal)

        return {
            "ip_address": ip_address,
            "session_id": session.session_id,
            "pagination": get_pagination(total_count, limit, offset),
            "filters_applied": {
                "meal_date": meal_date,
                "meal_type": meal_type
            },
            "meals": formatted_meals
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error retrieving saved meals: {str(e)}")