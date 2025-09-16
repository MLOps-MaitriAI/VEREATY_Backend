# utils/meals_generate_function.py

import json
import logging
import asyncio
from typing import Dict, List, Optional, Set
import os
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio
import base64
import json
import os
import logging
from dotenv import load_dotenv
import aiohttp
import requests
from PIL import Image
import io

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")


class GeminiImageGenerationService:
    """Service for generating meal images using Gemini API for enhanced descriptions + free image service"""
    
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.description_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # Free image generation APIs (you can switch between these)
        self.image_apis = [
            {
                "name": "pollinations",
                "url": "https://image.pollinations.ai/prompt/",
                "method": "GET"
            },
            {
                "name": "replicate_free", 
                "url": "https://api.replicate.com/v1/predictions",
                "method": "POST"
            }
        ]
        
    async def generate_enhanced_image_prompt(self, meal_name: str, description: str, cuisine_type: str) -> str:
        """Use Gemini to create an enhanced image generation prompt"""
        try:
            prompt = f"""
            You are a professional food photographer and AI image generation expert. 
            Create a detailed, visually rich prompt for generating a high-quality food photograph.
            
            Meal: {meal_name}
            Description: {description}
            Cuisine: {cuisine_type}
            
            Generate a detailed prompt that includes:
            - Specific visual details (colors, textures, garnishes)
            - Lighting style (natural, warm, professional)
            - Plating and presentation style
            - Camera angle and composition
            - Background and styling elements
            - Mood and atmosphere
            
            Format as a single paragraph, optimized for AI image generation.
            Focus on making the food look appetizing and professional.
            Include specific details about Indian food presentation if applicable.
            
            Output only the image generation prompt, nothing else.
            """
            
            response = await asyncio.to_thread(
                self.description_model.generate_content,
                prompt
            )
            
            enhanced_prompt = response.text.strip()
            logger.info(f"Enhanced prompt created for {meal_name}")
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error creating enhanced prompt: {str(e)}")
            # Fallback to basic prompt
            return f"Professional food photography of {meal_name}, {cuisine_type} cuisine, beautifully plated, natural lighting, high quality, appetizing"
    
    async def generate_meal_image(self, meal_name: str, description: str, cuisine_type: str) -> Optional[str]:
        """Generate an image using Gemini-enhanced prompt and free image service"""
        try:
            # Step 1: Get enhanced prompt from Gemini
            enhanced_prompt = await self.generate_enhanced_image_prompt(meal_name, description, cuisine_type)
            
            # Step 2: Generate image using free service
            image_data = await self._generate_with_pollinations(enhanced_prompt)
            
            if image_data:
                return image_data
            else:
                logger.warning(f"Image generation failed for {meal_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating image for {meal_name}: {str(e)}")
            return None
    
    async def _generate_with_pollinations(self, prompt: str) -> str | None:
        """Generate image using Pollinations AI (free service) and save locally"""
        try:
            # Clean and encode the prompt
            clean_prompt = prompt.replace(" ", "%20").replace(",", "%2C")
            image_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=512&height=512&model=flux&nologo=true"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        image_bytes = await response.read()

                        # Ensure local folder exists
                        folder = "static/generated_meals"
                        os.makedirs(folder, exist_ok=True)

                        # Save image with a unique name
                        image_name = f"{hash(prompt)}.png"
                        image_path = os.path.join(folder, image_name)
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        # Return URL to access via your server
                        # base_url = "http://192.168.29.82:8000"
                        return f"{folder}/{image_name}"
                    else:
                        logger.warning(f"Pollinations API returned status: {response.status}")
                        return None
                            
        except Exception as e:
            logger.error(f"Error with Pollinations API: {str(e)}")
            return None
    
    async def _generate_with_replicate_free(self, prompt: str) -> Optional[str]:
        """Alternative: Generate with Replicate's free tier (requires API key)"""
        try:
            # This would require REPLICATE_API_TOKEN in .env
            replicate_token = os.getenv("REPLICATE_API_TOKEN")
            if not replicate_token:
                return None
                
            headers = {
                "Authorization": f"Token {replicate_token}",
                "Content-Type": "application/json",
            }
            
            data = {
                "version": "ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4",
                "input": {
                    "prompt": prompt,
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 20
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.replicate.com/v1/predictions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        # Would need to poll for completion - simplified for demo
                        return None  # Implement polling logic
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"Error with Replicate API: {str(e)}")
            return None
    
    def get_fallback_image_url(self, meal_name: str, cuisine_type: str) -> str:
        """Return a placeholder image URL as fallback"""
        # You can also use Unsplash for better food placeholders
        unsplash_query = f"{meal_name.replace(' ', '%20')}%20{cuisine_type.replace(' ', '%20')}%20food"
        return f"https://source.unsplash.com/400x300/?{unsplash_query}"


class DishRecommendationService:
    """Professional dish recommendation service with Gemini-enhanced image generation"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 4048,
        }
        
        # Initialize Gemini-based image generation service
        self.image_service = GeminiImageGenerationService(api_key)

        # Enhanced prompts for each meal type with better descriptions
        self.meal_prompts = {
            "breakfast": (
                "You are a professional chef and nutritionist with over 15 years of experience. "
                "Generate unique Indian breakfast dishes with step-by-step recipe instructions, "
                "preparation details, and nutritional highlights. "
                "Create DETAILED, appetizing descriptions that highlight flavors, textures, aromas, and visual appeal. "
                "Include vivid descriptions of colors, plating style, and garnishes for image generation. "
                "Only Indian breakfast dishes. "
                "Do NOT include ingredient quantities. "
                "Ensure dishes are unique across all days."
            ),
            "lunch": (
                "You are a professional chef and nutritionist with over 15 years of experience. "
                "Generate unique Indian lunch dishes with full recipe steps and cooking instructions. "
                "Create DETAILED, appetizing descriptions that capture the essence, flavors, and cultural significance. "
                "Include vivid visual descriptions of colors, textures, and presentation style. "
                "Include nutritional highlights, but DO NOT add ingredient quantities. "
                "Only Indian lunch dishes. "
                "Ensure dishes are unique across all days."
            ),
            "dinner": (
                "You are a professional chef and nutritionist with over 15 years of experience. "
                "Generate unique Indian dinner dishes that are light yet satisfying, with complete "
                "recipes and preparation steps. "
                "Create DETAILED, mouth-watering descriptions that emphasize comfort, satisfaction, and authentic flavors. "
                "Include detailed visual descriptions for professional food photography. "
                "Include nutritional highlights, but DO NOT include ingredient quantities. "
                "Only Indian dinner dishes. "
                "Ensure dishes are unique across all days."
            ),
        }

        # global dish counter to keep meal_id unique
        self.global_meal_counter = 0

    async def generate_dishes_by_meal_type(
        self,
        meal_type: str,
        preferences: Dict,
        num_dishes: int = 3,
        exclude_dishes: Optional[Set[str]] = None,
        days: int = 1,
        generate_images: bool = True,
    ) -> List[Dict]:
        """Generate unique dishes for a specific meal type with recipes, across multiple days"""
        if meal_type not in ["breakfast", "lunch", "dinner"]:
            raise ValueError(f"Invalid meal type: {meal_type}")
        exclude_dishes = exclude_dishes or set()

        try:
            preference_context = self._build_preference_context(preferences)
            prompt = f"""
{self.meal_prompts[meal_type]}

USER PREFERENCES:
{preference_context}

REQUIREMENTS:
- Generate dishes for {days} days.
- For each day, generate exactly {num_dishes} distinct {meal_type} dishes.
- Each dish must be unique and not in: {', '.join(exclude_dishes) if exclude_dishes else 'None'}
- Include step-by-step recipe instructions
- Include cooking time, difficulty, dietary tags, main ingredients, spice level, region
- Include nutritional highlights with descriptive and numeric values
- Create DETAILED, appetizing descriptions (3-4 sentences) that make the dish irresistible
- Descriptions should include: flavors, textures, aromas, visual appeal, colors, and cultural context
- Add vivid visual details for professional food photography (colors, garnishes, plating style)
- Ensure no dish is repeated across different days.
- Do not include ingredient quantities anywhere.
- In nutritional only give protein, fats, calories (with proper g or kcal units).
- Add a confidence_score between 0.70 and 0.99 indicating how confident you are in this dish recommendation.

CRITICAL REQUIREMENTS:
1. Generate EXACTLY {days} days with meal types: {meal_type}
2. Each meal type must have EXACTLY {num_dishes} unique dishes per day
3. NO REPETITION: All dishes across all days must be completely unique
4. ONLY suggest dishes for: breakfast, lunch, dinner

OUTPUT FORMAT (JSON):
{{
    "days": [
        {{
            "day": 1,
            "dishes": [
                {{
                    "meal_id": 1,
                    "name": "Dish Name",
                    "description": "Detailed 3-4 sentence appetizing description highlighting flavors, textures, aromas, visual appeal, colors, and cultural significance with vivid imagery for professional food photography",
                    "meal_type": "{meal_type}",
                    "cuisine_type": "Regional cuisine",
                    "prep_time": "XX minutes",
                    "cooking_time": "XX minutes",
                    "difficulty": "Easy/Medium/Hard",
                    "dietary_tags": ["vegetarian/non-vegetarian"],
                    "spice_level": "Mild/Medium/Spicy",
                    "main_ingredients": ["ingredient1", "ingredient2"],
                    "nutritional": [
                        {{"name": "protein", "amount": "20g", "description": "protein-rich"}},
                        {{"name": "fats", "amount": "6g", "description": "healthy fats source"}},
                        {{"name": "calories", "amount": "320 kcal", "description": "calorie content"}}
                    ],
                    "region": "State/Region",
                    "recipe": [
                        "Step 1: ...",
                        "Step 2: ...",
                        "Step 3: ..."
                    ],
                    "confidence_score": 0.85
                }}
            ]
        }}
    ]
}}
"""
            dishes_data = await self._generate_with_retries(prompt)
            validated_dishes = await self._validate_dishes_across_days(
                dishes_data, meal_type, num_dishes, exclude_dishes, days, generate_images
            )
            return validated_dishes

        except Exception as e:
            logger.error(f"Error generating {meal_type} dishes: {str(e)}")
            return await self._get_fallback_dishes(meal_type, num_dishes, generate_images)

    async def generate_complete_meal_recommendations(
        self,
        preferences: Dict,
        include_meals: List[str] = ["breakfast", "lunch", "dinner"],
        dishes_per_meal: int = 3,
        days: int = 1,
        generate_images: bool = True,
    ) -> Dict[str, List[Dict]]:
        """Generate complete meal recommendations ensuring uniqueness across meals and days"""
        meal_recommendations = {}
        all_generated_dishes = set()

        for meal_type in include_meals:
            if meal_type not in ["breakfast", "lunch", "dinner"]:
                continue
            dishes = await self.generate_dishes_by_meal_type(
                meal_type=meal_type,
                preferences=preferences,
                num_dishes=dishes_per_meal,
                exclude_dishes=all_generated_dishes,
                days=days,
                generate_images=generate_images,
            )
            meal_recommendations[meal_type] = dishes
            all_generated_dishes.update(dish["name"].lower() for dish in dishes)
            await asyncio.sleep(0.5)

        return meal_recommendations

    def _build_preference_context(self, preferences: Dict) -> str:
        """Convert user preferences into prompt context"""
        context_parts = []
        for key, default in [
            ("dietary_style", "Any"),
            ("regional_cuisines", "Any"),
            ("spice_tolerance", "Medium"),
            ("health_conditions", "None"),
            ("food_allergies", "None"),
            ("family_needs", "Not needed"),
            ("fasting_observances", "None"),
            ("cooking_constraints", "None"),
            ("meal_complexity", "Simple"),
        ]:
            val = preferences.get(key, default)
            if val != default:
                context_parts.append(f"{key.replace('_',' ').title()}: {val}")
        return (
            "\n".join(context_parts)
            if context_parts
            else "No specific preferences provided"
        )

    async def _generate_with_retries(self, prompt: str) -> List[Dict]:
        """Generate dishes with retry and JSON parsing"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=self.generation_config,
                )
                response_text = response.text.strip()
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                dishes_data = json.loads(response_text)
                if "days" in dishes_data:
                    return dishes_data["days"]
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
        return []

    async def _validate_dishes_across_days(
        self, 
        days_data: List[Dict], 
        meal_type: str, 
        expected_count: int, 
        exclude_dishes: Set[str], 
        days: int,
        generate_images: bool = True
    ) -> List[Dict]:
        """Validate and ensure no repetition across days, generate images if enabled"""
        validated = []
        
        for day_entry in days_data:
            for i, dish in enumerate(day_entry.get("dishes", [])):
                name = dish.get("name", f"{meal_type.title()} {i+1}")
                if name.lower() in exclude_dishes:
                    continue

                # Ensure global unique meal_id
                self.global_meal_counter += 1
                dish["meal_id"] = self.global_meal_counter
                dish["meal_type"] = meal_type
                dish.setdefault("recipe", ["Prepare as per standard recipe steps"])

                # Ensure proper nutritional values
                dish["nutritional"] = dish.get(
                    "nutritional",
                    [
                        {"name": "protein", "amount": f"{20 + i*2}g", "description": "protein-rich"},
                        {"name": "fats", "amount": f"{6 + i}g", "description": "healthy fats source"},
                        {"name": "calories", "amount": f"{320 + i*20} kcal", "description": "calorie content"},
                    ],
                )
                dish["confidence_score"] = round(0.8 + (0.02 * (i % 10)), 2)

                # Generate image using Gemini-enhanced prompts
                if generate_images and self.image_service:
                    try:
                        logger.info(f"Generating Gemini-enhanced image for {name}")
                        image_data = await self.image_service.generate_meal_image(
                            name, 
                            dish.get("description", ""), 
                            dish.get("cuisine_type", "Indian")
                        )
                        dish["image_url"] = image_data or self.image_service.get_fallback_image_url(
                            name, dish.get("cuisine_type", "Indian")
                        )
                        dish["image_generation_method"] = "gemini_enhanced"
                    except Exception as img_error:
                        logger.error(f"Image generation failed for {name}: {img_error}")
                        dish["image_url"] = self.image_service.get_fallback_image_url(
                            name, dish.get("cuisine_type", "Indian")
                        )
                        dish["image_generation_method"] = "fallback"
                else:
                    # Use Unsplash fallback for better food images
                    unsplash_query = f"{name.replace(' ', '%20')}%20Indian%20food"
                    dish["image_url"] = f"https://source.unsplash.com/400x300/?{unsplash_query}"
                    dish["image_generation_method"] = "unsplash_fallback"

                validated.append(dish)
                exclude_dishes.add(name.lower())

        return validated

    async def _get_fallback_dishes(self, meal_type: str, num_dishes: int, generate_images: bool = True) -> List[Dict]:
        """Fallback dishes with recipe if AI fails"""
        dishes = []
        for i in range(num_dishes):
            dish = await self._create_fallback_dish(meal_type, i + 1, generate_images)
            dishes.append(dish)
        return dishes

    async def _create_fallback_dish(self, meal_type: str, meal_id: int, generate_images: bool = True) -> Dict:
        """Generic fallback dish with recipe, nutritional info, and image"""
        self.global_meal_counter += 1
        
        dish_name = f"Traditional {meal_type.title()} {meal_id}"
        description = f"A delicious and authentic {meal_type} dish featuring traditional Indian spices and cooking techniques, perfectly balanced for nutrition and flavor, representing the rich culinary heritage of India with vibrant colors and aromatic presentation."
        
        dish = {
            "meal_id": self.global_meal_counter,
            "name": dish_name,
            "description": description,
            "meal_type": meal_type,
            "cuisine_type": "Indian",
            "prep_time": "15 minutes",
            "cooking_time": "30 minutes",
            "difficulty": "Medium",
            "dietary_tags": ["vegetarian"],
            "spice_level": "Medium",
            "main_ingredients": ["vegetables", "spices", "oil"],
            "nutritional": [
                {"name": "protein", "amount": "22g", "description": "protein-rich"},
                {"name": "fats", "amount": "6g", "description": "healthy fats source"},
                {"name": "calories", "amount": "320 kcal", "description": "calorie content"},
            ],
            "region": "Pan-Indian",
            "recipe": [
                "Step 1: Prepare all ingredients and wash them thoroughly.",
                "Step 2: Heat oil in a pan and add aromatic spices.",
                "Step 3: Cook ingredients as per traditional method with proper seasoning.",
                "Step 4: Garnish and serve hot with traditional accompaniments.",
            ],
            "confidence_score": 0.75,
        }
        
        # Generate image for fallback dish
        if generate_images and self.image_service:
            try:
                image_data = await self.image_service.generate_meal_image(
                    dish_name, description, "Indian"
                )
                dish["image_url"] = image_data or self.image_service.get_fallback_image_url(
                    dish_name, "Indian"
                )
                dish["image_generation_method"] = "gemini_enhanced_fallback"
            except Exception:
                dish["image_url"] = self.image_service.get_fallback_image_url(dish_name, "Indian")
                dish["image_generation_method"] = "unsplash_fallback"
        else:
            unsplash_query = f"{dish_name.replace(' ', '%20')}%20Indian%20food"
            dish["image_url"] = f"https://source.unsplash.com/400x300/?{unsplash_query}"
            dish["image_generation_method"] = "unsplash_fallback"
        
        return dish


async def get_dish_recommendations(
    preferences: Dict,
    meal_types: List[str] = ["breakfast", "lunch", "dinner"],
    dishes_per_meal: int = 3,
    api_key: str = None,
    exclude_dishes: Optional[Set[str]] = None,
    days: int = 1,
    generate_images: bool = True,
) -> Dict[str, List[Dict]]:
    """
    Main function to get dish recommendations with Gemini-enhanced image generation
    
    Args:
        preferences: User dietary preferences
        meal_types: Types of meals to generate
        dishes_per_meal: Number of dishes per meal type
        api_key: Gemini API key
        exclude_dishes: Dishes to exclude from generation
        days: Number of days to generate for
        generate_images: Whether to generate images (uses Gemini + free services)
    
    Returns:
        Dictionary with meal recommendations including enhanced images
    """
    if not api_key:
        raise ValueError("Gemini API key is required")
    
    service = DishRecommendationService(api_key)
    return await service.generate_complete_meal_recommendations(
        preferences, meal_types, dishes_per_meal, days, generate_images
    )


def extract_time_minutes(time_str: str) -> int:
            """Extract minutes from time string like '20 minutes' or '1 hour 30 minutes'"""
            if not time_str:
                return 0
            
            time_str = time_str.lower()
            minutes = 0
            
            if 'hour' in time_str:
                hours_part = time_str.split('hour')[0]
                hours = int(''.join(filter(str.isdigit, hours_part)) or 0)
                minutes += hours * 60
            
            if 'minute' in time_str:
                minute_part = time_str.split('minute')[0]
                if 'hour' in minute_part:
                    minute_part = minute_part.split('hour')[-1]
                mins = int(''.join(filter(str.isdigit, minute_part)) or 0)
                minutes += mins
                
            return minutes or 30  