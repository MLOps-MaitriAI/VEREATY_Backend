from typing import Dict, List, Optional
from pydantic import BaseModel, validator
from api.v1.endpoints.dish_recommendation.meals_generate import VALID_TIME_LIMITS, normalize_meal_types

# --------------------------------- user interaction --------------------------
class DietaryPreference(BaseModel):
    dietary_style: str
    regional_cuisines: str
    allergies: str
    fasting_practices: str
    health_concerns: str
    children_in_household: str
    child_friendly_meals: str
    protein_preferences: str
    spice_level: str
    plan_type: str = "weekly"
    meal_types: Optional[List[str]] = None

class CustomMealPlanRequest(BaseModel):
    days: int
    
    @validator('days')
    def validate_days(cls, v):
        if not 2 <= v <= 6:
            raise ValueError('Days must be between 2 and 6')
        return v

class AdvancedMealPlanRequest(BaseModel):
    days: int
    meal_types: Optional[List[str]] = None
    
    @validator('days')
    def validate_days(cls, v):
        if not 1 <= v <= 7:
            raise ValueError('Days must be between 1 and 7')
        return v
    
    @validator('meal_types')
    def validate_meal_types(cls, v):
        normalized = normalize_meal_types(v or [])
        if not normalized:
            raise ValueError('At least one valid meal type required')
        return normalized

class QuickMealRequest(BaseModel):
    meal_types: List[str]
    
    @validator('meal_types')
    def validate_meal_types(cls, v):
        normalized = normalize_meal_types(v)
        if not normalized:
            raise ValueError('At least one valid meal type required')
        return normalized

class QuickPrepMealRequest(BaseModel):
    meal_types: List[str]
    time_limit: int
    
    @validator('meal_types')
    def validate_meal_types(cls, v):
        normalized = normalize_meal_types(v)
        if not normalized:
            raise ValueError('At least one valid meal type required')
        return normalized
    
    @validator('time_limit')
    def validate_time_limit(cls, v):
        if not VALID_TIME_LIMITS[0] <= v <= VALID_TIME_LIMITS[1]:
            raise ValueError(f'Time limit must be between {VALID_TIME_LIMITS[0]} and {VALID_TIME_LIMITS[1]} minutes')
        return v

class ReplaceDishRequest(BaseModel):
    replace_dish: str
    
    @validator('replace_dish')
    def validate_dish_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Dish name cannot be empty')
        return v.strip()

class Dish(BaseModel):
    meal_id: int
    name: str
    description: str
    recipe: Optional[str] = None

class MealPlanDay(BaseModel):
    day: str
    meals: Dict[str, List[Dish]]

class MealPlanResponse(BaseModel):
    user_id: int
    plan_type: str
    days: List[MealPlanDay]
    grocery_list: Dict[str, List[str]]

class RecipeResponse(BaseModel):
    dish_name: str
    recipe_markdown: str
    region_info: Dict = {}

class RegionalProfileResponse(BaseModel):
    profiles: List[Dict[str, Dict]]