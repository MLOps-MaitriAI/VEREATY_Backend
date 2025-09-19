import asyncio
import json
import logging
import os
import re
from typing import Dict, Optional, List

import google.generativeai as genai
import aiohttp

logger = logging.getLogger(__name__)

# -------------------------------
# Image Generator
# -------------------------------
class MealImageGenerator:
    def __init__(self, description_model):
        self.description_model = description_model

    async def generate_enhanced_image_prompt(self, meal_name: str, description: str, cuisine_type: str) -> str:
        try:
            prompt = f"""
            You are a professional food photographer and AI image generation expert. 
            Create a detailed, visually rich prompt for generating a high-quality food photograph.
            
            Meal: {meal_name}
            Description: {description}
            Cuisine: {cuisine_type}
            
            Generate a detailed prompt with:
            - Visual details (colors, textures, garnishes)
            - Lighting style
            - Plating and presentation
            - Camera angle
            - Background and styling
            - Mood and atmosphere
            
            Format as a single paragraph, optimized for AI image generation.
            """
            response = await asyncio.to_thread(
                self.description_model.generate_content,
                prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error creating enhanced prompt: {str(e)}")
            return f"Professional food photography of {meal_name}, {cuisine_type} cuisine, natural lighting"

    async def generate_meal_image(self, meal_name: str, description: str, cuisine_type: str) -> Optional[str]:
        try:
            enhanced_prompt = await self.generate_enhanced_image_prompt(meal_name, description, cuisine_type)
            return await self._generate_with_pollinations(enhanced_prompt)
        except Exception as e:
            logger.error(f"Error generating image for {meal_name}: {str(e)}")
            return None

    async def _generate_with_pollinations(self, prompt: str) -> Optional[str]:
        try:
            clean_prompt = prompt.replace(" ", "%20").replace(",", "%2C")
            image_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=512&height=512&model=flux&nologo=true"

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        folder = "static/generated_meals"
                        os.makedirs(folder, exist_ok=True)

                        image_name = f"{hash(prompt)}.png"
                        image_path = os.path.join(folder, image_name)
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        return f"{folder}/{image_name}"
                    else:
                        logger.warning(f"Pollinations API returned status: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error with Pollinations API: {str(e)}")
            return None


# -------------------------------
# Gemini Meal Generator
# -------------------------------
def generate_meals_llm(
    ingredient_names: List[str],
    meal_type: str,
    num_dishes: int,
    preferences: Dict,
    generate_images: bool
):
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise Exception("Missing GEMINI_API_KEY in environment")

    genai.configure(api_key=gemini_api_key)
    description_model = genai.GenerativeModel("gemini-2.0-flash-exp")

    prompt = f"""
    You are a professional chef and nutritionist with over 15 years of experience. Generate {num_dishes} {meal_type} dishes
    using ONLY these pantry ingredients: {', '.join(ingredient_names)}.

    User preferences: {json.dumps(preferences)}

    Return strictly valid JSON, do not include extra text or explanations.
    Format example:
    [
      {{
        "dishes": [
          {{
            "name": "Dish Name",
            "description": "Short description",
            "ingredients": ["ingredient1", "ingredient2"],
            "prep_time": 20,
            "nutritional": [
              {{"type": "Calories", "amount": "200 kcal"}},
              {{"type": "Protein", "amount": "10 g"}},
              {{"type": "Carbs", "amount": "30 g"}},
              {{"type": "Fat", "amount": "5 g"}}
            ],
            "confidence_score": 95,
            "instructions": [
              {{"step_number": 1, "instruction_text": "Do this"}}
            ]
          }}
        ]
      }}
    ]
    """

    response = description_model.generate_content(prompt)
    content = response.text.strip()

    # Try to extract JSON from triple backticks or clean the text
    match = re.search(r"```(?:json)?\s*(\[\s*{.*}\s*])\s*```", content, re.DOTALL)
    json_text = match.group(1) if match else content

    # Remove any leading text before first "[" and trailing text after last "]"
    json_text = re.sub(r"^[^\[]*\[", "[", json_text, count=1)
    json_text = re.sub(r"\][^\]]*$", "]", json_text, count=1)

    try:
        generated_dishes = json.loads(json_text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Gemini output: {content}")
        raise Exception(f"Invalid JSON returned by Gemini. Check logs for raw output.")

    # Initialize images to None if requested
    if generate_images:
        for day in generated_dishes:
            for dish in day.get("dishes", []):
                dish["image_url"] = None

    return generated_dishes

