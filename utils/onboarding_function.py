# =============================================================================
# FIXED PRODUCTION-READY MEAL PLANNING ONBOARDING SYSTEM - DYNAMIC LLM ONLY
# =============================================================================

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import pytz
import json
import uuid
import logging
import re
from enum import Enum
from api.v1.models.onboarding.onboarding_sessions import OnboardingSession
# Third-party imports
import google.generativeai as genai

from utils.prompt import DYNAMIC_SYSTEM_PROMPT, PREFERENCE_MAPPINGS, PreferenceCategory

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# ENHANCED CONVERSATION ENGINE - PURE DYNAMIC LLM APPROACH
# =============================================================================

class DynamicConversationEngine:
    """Fully dynamic conversation engine - LLM generates all preference keys"""
    
    def __init__(self, model_name: str = 'gemini-2.0-flash-exp'):
        try:
            self.model = genai.GenerativeModel(model_name)
            self.generation_config = {
                'temperature': 0.75,  
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 4080,  
            }
            logger.info(f"Initialized conversation engine with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize conversation engine: {str(e)}")
            raise HTTPException(status_code=500, detail="AI service initialization failed")
        
    
    def generate_next_question(
        self,
        conversation_history: List[Dict],
        user_input: str = "",
        question_count: int = 11
    ) -> Dict[str, Any]:
        """Generate fully dynamic questions with dynamic preference keys"""
        try:
            answered_questions = [msg for msg in conversation_history if msg.get("answer")]
            total_answered = len(answered_questions)

            logger.info(f"Generating dynamic question #{total_answered + 1}/10")

            if total_answered >= 10:
                logger.info("All 10 questions answered. Generating completion summary...")
                return self._generate_completion_response(conversation_history)

            # Build context and get used preference keys
            context = self._build_comprehensive_context(conversation_history)
            used_preference_keys = self._extract_used_preference_keys(conversation_history)

            # Enhanced dynamic prompt for fully dynamic preference keys
            enhanced_prompt = self._build_fully_dynamic_prompt(
                context, user_input, total_answered, used_preference_keys
            )

            # Generate with multiple attempts for quality
            response = self._generate_with_intelligent_retry(enhanced_prompt)
            
            # Parse with flexible approach
            parsed_response = self._flexible_parse_response(response.text, total_answered)

            # Validate and enhance with dynamic keys
            final_response = self._enhance_fully_dynamic_response(
                parsed_response, used_preference_keys, total_answered
            )

            # Quality check - if still not good enough, try one more time
            if not self._is_quality_response(final_response):
                logger.info("Response quality insufficient, generating alternative...")
                alternative_response = self._generate_alternative_dynamic_question(
                    conversation_history, used_preference_keys, total_answered
                )
                if self._is_quality_response(alternative_response):
                    final_response = alternative_response

            logger.info(f"Generated dynamic question with key '{final_response.get('preference_key')}': '{final_response.get('question', '')[:100]}...'")
            return final_response

        except Exception as e:
            logger.error(f"Error in dynamic generation: {str(e)}")
            return self._emergency_dynamic_generation(len(conversation_history))

    def _build_fully_dynamic_prompt(self, context: str, user_input: str, question_num: int, used_keys: set) -> str:
        """Build prompt that ensures priority categories are covered with dynamic questions"""
        
        # Essential categories that must be covered
        priority_categories = [
            "dietary_style",      # What food do you eat?
            "spice_tolerance",    # How spicy do you like food?
            "food_allergies",     # Any foods you can't eat?
            "regional_cuisines",  # What kind of Indian food do you like?
            "health_conditions",  # Any health issues with food?
            "family_needs",       # Do you cook for family?
            "cooking_constraints", # How much time do you have to cook?
            "meal_complexity",    # Do you like simple or fancy meals?
            "fasting_observances", # Do you fast for religious reasons?
            "general_preference"  # Any other food likes/dislikes?
        ]
        
        # Find next priority category to cover
        uncovered_priority = [cat for cat in priority_categories if cat not in used_keys]
        next_priority = uncovered_priority[0] if uncovered_priority else "general_preference"
        
        # Get guidance for this category
        category_guidance = self._get_priority_category_guidance(next_priority)
        
        base_prompt = f"""
You are a friendly meal planning expert helping someone understand their food preferences.
You need to ask simple, everyday questions to learn about their eating habits.

CONVERSATION SO FAR:
{context}

USER JUST SAID: {user_input}

THIS IS QUESTION {question_num + 1} OF 10 TOTAL QUESTIONS.

ESSENTIAL CATEGORIES TO COVER: {', '.join(priority_categories)}
ALREADY COVERED: {', '.join(used_keys) if used_keys else 'None'}
STILL NEED TO COVER: {', '.join(uncovered_priority) if uncovered_priority else 'All covered'}

PRIORITY FOR THIS QUESTION: {next_priority}
{category_guidance}

YOUR TASK:
1. Use the preference_key: {next_priority}
2. Ask a simple, friendly question about this specific food preference area
3. Provide 4 realistic options + "Other"

QUESTION RULES:
- Keep it simple and conversational (max 12 words)
- Ask about real everyday food situations
- Connect to previous answers when possible
- Use "you" and friendly language

RESPONSE FORMAT (EXACT FORMAT REQUIRED):
Question: [Simple friendly question about {next_priority.replace('_', ' ')} - max 12 words]

A) [Realistic option 1]  
B) [Realistic option 2]  
C) [Realistic option 3]  
D) [Realistic option 4]  
E) Other (please specify)

Preference_Key: {next_priority}

EXAMPLE QUESTIONS FOR EACH CATEGORY:

dietary_style: "What type of food do you usually eat?"
- A) Vegetarian only  B) Non-vegetarian  C) Vegan  D) Jain food

spice_tolerance: "How spicy do you like your food?"
- A) No spice at all  B) Mild spice  C) Medium spicy  D) Very spicy

food_allergies: "Are there any foods you cannot eat?"
- A) No restrictions  B) Lactose intolerant  C) Gluten-free  D) Nut allergies

regional_cuisines: "Which regional cuisine do you prefer most?"
- A) North Indian  B) South Indian  C) Gujarati  D) Bengali

health_conditions: "Do you have any health conditions affecting food?"
- A) None  B) Diabetes  C) High blood pressure  D) Thyroid

family_needs: "Do you need to consider family preferences?"
- A) Just for me  B) Sometimes  C) Always needed  D) Very important

cooking_constraints: "How much time do you have for cooking?"
- A) Plenty of time  B) 30 minutes max  C) Quick meals only  D) Very little time

meal_complexity: "What cooking style do you prefer?"
- A) Simple daily food  B) Sometimes elaborate  C) Love detailed cooking  D) Depends on occasion

fasting_observances: "Do you follow any fasting practices?"
- A) No fasting  B) Weekly vrat  C) Navratri  D) Ekadashi

general_preference: "Any other food preferences to consider?"
- A) Low oil  B) High protein  C) Traditional style  D) Modern fusion

Make sure to:
1. Use EXACTLY the preference_key: {next_priority}
2. Ask a question that clearly relates to this category
3. Provide options that make sense for this category

"""

        return base_prompt
    
    def _get_priority_category_guidance(self, category: str) -> str:
        """Get specific guidance for priority categories"""
        guidance = {
            "dietary_style": """
Ask about their primary eating style - vegetarian, non-vegetarian, vegan, Jain, etc.
This is fundamental for all meal planning. Keep it simple and clear.
""",
            "spice_tolerance": """
Ask about their spice preference level - mild, medium, spicy, very spicy.
This affects every recipe recommendation. Use everyday language.
""",
            "food_allergies": """
Ask if they have any foods they cannot eat due to allergies or intolerances.
Critical for safety. Include common ones like dairy, gluten, nuts.
""",
            "regional_cuisines": """
Ask about their preferred regional Indian cuisine style.
This helps narrow down recipe types. Include North/South Indian, Gujarati, Bengali, etc.
""",
            "health_conditions": """
Ask if they have any health conditions that affect their diet.
Include common ones like diabetes, high BP, thyroid. Important for meal planning.
""",
            "family_needs": """
Ask if they need to consider family members' preferences when cooking.
This affects portion sizes and recipe choices. Keep it practical.
""",
            "cooking_constraints": """
Ask about their available cooking time and constraints.
Critical for suggesting appropriate recipes. Focus on time availability.
""",
            "meal_complexity": """
Ask about their preferred cooking style - simple daily food vs elaborate cooking.
This determines recipe complexity levels. Keep it relatable.
""",
            "fasting_observances": """
Ask if they follow any religious fasting practices.
Important for meal timing and ingredient restrictions. Include common vrats.
""",
            "general_preference": """
Ask about any other specific food preferences or requirements.
Catch-all for anything not covered. Keep it open-ended but focused.
"""
        }
        
        return guidance.get(category, "Ask a simple question about their food preferences.")
    
    def _extract_used_preference_keys(self, conversation_history: List[Dict]) -> set:
        """Extract all preference keys that have been used"""
        used_keys = set()
        for msg in conversation_history:
            if msg.get("preference_key") and msg.get("answer"):
                used_keys.add(msg["preference_key"])
        
        logger.info(f"Used preference keys: {used_keys}")
        return used_keys

    def _generate_with_intelligent_retry(self, prompt: str, max_attempts: int = 3) -> Any:
        """Generate with intelligent retry and prompt refinement"""
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"LLM generation attempt {attempt + 1}/{max_attempts}")
                
                # Modify prompt slightly for retries
                if attempt > 0:
                    retry_prompt = prompt + f"\n\nPREVIOUS ATTEMPT {attempt} FAILED. Please follow the EXACT format and create a truly unique preference_key."
                else:
                    retry_prompt = prompt
                
                response = self.model.generate_content(
                    retry_prompt,
                    generation_config=self.generation_config
                )
                
                if response and response.text and len(response.text.strip()) > 20:
                    logger.info(f"LLM generated response (attempt {attempt + 1}): {response.text[:150]}...")
                    return response
                else:
                    logger.warning(f"Empty or too short response on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_attempts - 1:
                    raise
        
        raise Exception("All intelligent generation attempts failed")

    def _flexible_parse_response(self, ai_text: str, question_num: int) -> Dict[str, Any]:
        """Flexible parsing that extracts dynamic preference keys"""
        try:
            logger.info(f"Parsing dynamic LLM response: {ai_text[:200]}...")
            
            response = {
                "question": "",
                "options": [],
                "preference_key": None,
                "is_complete": False
            }
            
            if not ai_text or len(ai_text.strip()) < 10:
                raise ValueError("Response too short or empty")
            
            lines = [line.strip() for line in ai_text.split('\n') if line.strip()]
            
            # Extract question (multiple patterns)
            question_patterns = [
                r'^Question:\s*(.+)$',
                r'^Q\d*[:.]\s*(.+)$', 
                r'^\d+[.)]\s*(.+\?)$',
                r'^(.+\?)$'  # Any line ending with ?
            ]
            
            for line in lines:
                if response["question"]:
                    break
                    
                for pattern in question_patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        response["question"] = match.group(1).strip()
                        logger.info(f"Extracted question: {response['question']}")
                        break
                
                # If no pattern match but looks like a question
                if not response["question"] and ('?' in line or len(line) > 20):
                    if any(word in line.lower() for word in ['what', 'which', 'how', 'do you', 'would you']):
                        response["question"] = line
                        logger.info(f"Inferred question: {response['question']}")
            
            # Extract options (flexible patterns)
            option_patterns = [
                r'^[A-E][.):\s]\s*(.+)$',
                r'^[1-5][.)]\s*(.+)$',
                r'^\*\s*(.+)$',  # Bullet points
                r'^-\s*(.+)$'    # Dashes
            ]
            
            for line in lines:
                option_found = False
                for pattern in option_patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        option_text = match.group(1).strip()
                        if option_text and len(option_text) > 1:
                            response["options"].append(option_text)
                            option_found = True
                            break
                
                if option_found:
                    continue
            
            # Extract dynamic preference_key
            preference_patterns = [
                r'Preference_Key:\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                r'PreferenceKey:\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                r'Key:\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                r'Category:\s*([a-zA-Z_][a-zA-Z0-9_]*)'
            ]
            
            for pattern in preference_patterns:
                match = re.search(pattern, ai_text, re.IGNORECASE)
                if match:
                    response["preference_key"] = match.group(1).lower()
                    logger.info(f"Extracted dynamic preference_key: {response['preference_key']}")
                    break
            
            # If no preference key found, generate one from question
            if not response["preference_key"] and response["question"]:
                response["preference_key"] = self._generate_preference_key_from_question(
                    response["question"], question_num
                )
                logger.info(f"Generated preference_key from question: {response['preference_key']}")
            
            # Ensure we have enough options
            while len(response["options"]) < 4:
                response["options"].append(f"Option {len(response['options']) + 1}")
            
            # Ensure "Other" is last option
            response["options"] = response["options"][:4]
            if not any("other" in opt.lower() for opt in response["options"]):
                response["options"].append("Other (please specify)")
            
            logger.info(f"Parsed dynamic response: Q='{response['question'][:50]}...', Options={len(response['options'])}, Key={response['preference_key']}")
            return response
            
        except Exception as e:
            logger.error(f"Error in flexible parsing: {str(e)}")
            raise ValueError(f"Failed to parse LLM response: {str(e)}")

    def _generate_preference_key_from_question(self, question: str, question_num: int) -> str:
        """Generate dynamic preference key from question content"""
        question_lower = question.lower()
        
        # Extract key concepts and convert to preference_key format
        key_concepts = []
        
        # Common food-related terms to preference keys
        concept_mappings = {
            "breakfast": "breakfast",
            "lunch": "lunch", 
            "dinner": "dinner",
            "snack": "snack",
            "spice": "spice",
            "cooking": "cooking",
            "meal": "meal",
            "food": "food",
            "eat": "eating",
            "drink": "beverage",
            "time": "timing",
            "prefer": "preference",
            "like": "preference",
            "portion": "portion",
            "vegetable": "vegetable",
            "fruit": "fruit",
            "protein": "protein",
            "grain": "grain",
            "dairy": "dairy",
            "sweet": "sweet",
            "salty": "salty",
            "hot": "temperature",
            "cold": "temperature",
            "texture": "texture",
            "budget": "budget",
            "shop": "shopping",
            "leftover": "leftover",
            "weekend": "weekend",
            "season": "seasonal",
            "outside": "dining_out",
            "restaurant": "dining_out",
            "kitchen": "kitchen",
            "equipment": "equipment",
            "prep": "preparation"
        }
        
        # Find concepts in question
        for word, concept in concept_mappings.items():
            if word in question_lower:
                if concept not in key_concepts:
                    key_concepts.append(concept)
        
        # Additional specific patterns
        if "how often" in question_lower or "frequency" in question_lower:
            key_concepts.append("frequency")
        elif "how much" in question_lower or "amount" in question_lower:
            key_concepts.append("amount")
        elif "when" in question_lower:
            key_concepts.append("timing")
        elif "where" in question_lower:
            key_concepts.append("location")
        elif "what type" in question_lower or "which" in question_lower:
            key_concepts.append("type")
        
        # Generate preference key
        if key_concepts:
            if len(key_concepts) == 1:
                preference_key = f"{key_concepts[0]}_preference"
            else:
                # Combine first two concepts
                preference_key = f"{key_concepts[0]}_{key_concepts[1]}"
        else:
            # Fallback based on question number
            fallback_keys = [
                "food_habits", "eating_style", "meal_pattern", "dietary_choice",
                "cooking_method", "flavor_profile", "portion_control", "meal_timing",
                "nutrition_focus", "food_enjoyment"
            ]
            preference_key = fallback_keys[question_num % len(fallback_keys)]
        
        # Ensure valid format
        preference_key = re.sub(r'[^a-z0-9_]', '_', preference_key.lower())
        preference_key = re.sub(r'_+', '_', preference_key).strip('_')
        
        return preference_key

    def _enhance_fully_dynamic_response(
        self, parsed_response: Dict, used_keys: set, question_num: int
    ) -> Dict[str, Any]:
        """Enhance response ensuring unique dynamic preference keys"""
        try:
            # Ensure question quality
            question = parsed_response.get("question", "").strip()
            if not question or len(question) < 10:
                question = f"What's your preference for meal planning? (Question {question_num + 1})"
            
            # Ensure good options
            options = parsed_response.get("options", [])
            if len(options) < 4:
                options = self._generate_contextual_options(question, question_num)
            
            # Ensure unique dynamic preference key
            preference_key = parsed_response.get("preference_key")
            if not preference_key or preference_key in used_keys:
                preference_key = self._generate_unique_preference_key(used_keys, question, question_num)
            
            return {
                "question": question,
                "options": options[:4] + ["Other (please specify)"],
                "preference_key": preference_key,
                "is_complete": False
            }
            
        except Exception as e:
            logger.error(f"Error enhancing response: {str(e)}")
            return self._emergency_dynamic_generation(question_num)

    def _generate_unique_preference_key(self, used_keys: set, question: str, question_num: int) -> str:
        """Generate a unique preference key not in used_keys"""
        base_key = self._generate_preference_key_from_question(question, question_num)
        
        # If base key is unique, use it
        if base_key not in used_keys:
            return base_key
        
        # Try variations
        for i in range(1, 10):
            variant_key = f"{base_key}_{i}"
            if variant_key not in used_keys:
                return variant_key
        
        # Fallback with timestamp-like suffix
        import time
        timestamp_suffix = str(int(time.time()))[-3:]
        fallback_key = f"preference_{timestamp_suffix}"
        
        return fallback_key

    def _generate_alternative_dynamic_question(
        self, conversation_history: List[Dict], used_keys: set, question_num: int
    ) -> Dict[str, Any]:
        """Generate alternative with completely new dynamic preference key"""
        try:
            # Generate a completely new preference key
            new_key = self._generate_creative_preference_key(used_keys, question_num)
            
            # Simple dynamic questions with creative keys
            creative_questions = {
                f"snacking_style_{question_num}": {
                    "question": "How do you usually snack?",
                    "options": ["Healthy snacks only", "Whatever's available", "Sweet treats", "Salty/savory snacks"]
                },
                f"cooking_motivation_{question_num}": {
                    "question": "What motivates your cooking?",
                    "options": ["Health benefits", "Taste and flavor", "Time saving", "Cost saving"]
                },
                f"meal_satisfaction_{question_num}": {
                    "question": "What makes a meal satisfying?",
                    "options": ["Large portions", "Rich flavors", "Nutritional value", "Comfort feeling"]
                },
                f"food_exploration_{question_num}": {
                    "question": "How adventurous are you with food?",
                    "options": ["Love trying new things", "Sometimes try new", "Stick to favorites", "Very particular"]
                },
                f"eating_environment_{question_num}": {
                    "question": "Where do you prefer eating?",
                    "options": ["At dining table", "While watching TV", "In kitchen", "Anywhere convenient"]
                }
            }
            
            # Select a question that uses a key not in used_keys
            for key, data in creative_questions.items():
                if key not in used_keys:
                    return {
                        "question": data["question"],
                        "options": data["options"] + ["Other (please specify)"],
                        "preference_key": key,
                        "is_complete": False
                    }
            
            # Ultimate fallback
            unique_key = f"custom_preference_{question_num}_{len(used_keys)}"
            return {
                "question": "What other food preferences should we know?",
                "options": ["Texture preferences", "Temperature preferences", "Flavor combinations", "Eating schedule", "Other (please specify)"],
                "preference_key": unique_key,
                "is_complete": False
            }
            
        except Exception as e:
            logger.error(f"Error generating alternative: {str(e)}")
            return self._emergency_dynamic_generation(question_num)

    def _generate_creative_preference_key(self, used_keys: set, question_num: int) -> str:
        """Generate creative preference keys"""
        creative_bases = [
            "flavor_balance", "meal_rhythm", "cooking_confidence", "ingredient_variety",
            "portion_awareness", "eating_pace", "food_temperature", "texture_variety",
            "cooking_creativity", "meal_planning", "leftover_usage", "seasonal_adaptation",
            "social_eating", "comfort_foods", "healthy_balance", "cooking_tools",
            "shopping_style", "food_storage", "meal_preparation", "eating_habits"
        ]
        
        # Find unused base
        for base in creative_bases:
            test_key = f"{base}_{question_num}"
            if test_key not in used_keys:
                return test_key
        
        # Generate completely unique key
        import time
        unique_suffix = str(int(time.time()))[-4:]
        return f"dynamic_pref_{unique_suffix}"

    def _generate_contextual_options(self, question: str, question_num: int) -> List[str]:
        """Generate contextual options based on question content"""
        question_lower = question.lower()
        
        # Context-based option sets
        if any(word in question_lower for word in ["snack", "snacking"]):
            return ["Rarely snack", "Healthy snacks", "Whatever available", "Multiple times daily"]
        elif any(word in question_lower for word in ["cook", "cooking"]):
            return ["Love cooking", "Cook when needed", "Quick meals only", "Avoid cooking"]
        elif any(word in question_lower for word in ["portion", "amount"]):
            return ["Small portions", "Medium portions", "Large portions", "Varies by mood"]
        elif any(word in question_lower for word in ["time", "timing", "when"]):
            return ["Very regular", "Somewhat regular", "Flexible timing", "No set schedule"]
        elif any(word in question_lower for word in ["prefer", "like", "favorite"]):
            return ["Strong preferences", "Some preferences", "Open to most", "Very flexible"]
        else:
            return ["Yes, always", "Sometimes", "Rarely", "Never"]

    def _is_quality_response(self, response: Dict) -> bool:
        """Check if response meets quality standards"""
        try:
            question = response.get("question", "")
            options = response.get("options", [])
            preference_key = response.get("preference_key")
            
            # Quality checks
            if not question or len(question.strip()) < 10:
                return False
            
            if len(options) != 5:  # 4 + Other
                return False
            
            if not preference_key or not re.match(r'^[a-z][a-z0-9_]*$', preference_key):
                return False
            
            # Check for meaningful content
            if question.count(" ") < 3:  # Too short
                return False
            
            return True
            
        except Exception:
            return False

    def _emergency_dynamic_generation(self, question_num: int) -> Dict[str, Any]:
        """Emergency generation with guaranteed dynamic key"""
        try:
            import time
            unique_suffix = str(int(time.time()))[-4:]
            
            emergency_questions = [
                {
                    "question": "What's most important in your daily meals?",
                    "options": ["Taste and flavor", "Health benefits", "Quick preparation", "Cost effectiveness"],
                    "key": f"meal_priority_{unique_suffix}"
                },
                {
                    "question": "How flexible are your eating times?",
                    "options": ["Very regular schedule", "Somewhat flexible", "Quite flexible", "No fixed times"],
                    "key": f"eating_flexibility_{unique_suffix}"
                },
                {
                    "question": "What cooking style suits you?",
                    "options": ["Simple and quick", "Traditional methods", "Modern techniques", "Whatever works"],
                    "key": f"cooking_approach_{unique_suffix}"
                }
            ]
            
            selected = emergency_questions[question_num % len(emergency_questions)]
            
            return {
                "question": selected["question"],
                "options": selected["options"] + ["Other (please specify)"],
                "preference_key": selected["key"],
                "is_complete": False
            }
            
        except Exception as e:
            logger.error(f"Emergency generation failed: {str(e)}")
            return {
                "question": "What would you like us to know about your food preferences?",
                "options": ["I have specific dietary needs", "I'm open to suggestions", "I like traditional food", "I enjoy variety", "Other (please specify)"],
                "preference_key": f"general_food_pref_{question_num}",
                "is_complete": False
            }

    def _build_comprehensive_context(self, conversation: List[Dict]) -> str:
        """Build detailed context for LLM"""
        if not conversation:
            return "Starting fresh onboarding conversation"
        
        context_parts = ["CONVERSATION HISTORY:"]
        
        for i, msg in enumerate(conversation, 1):
            if msg.get("question"):
                context_parts.append(f"Q{i}: {msg['question']}")
                
                if msg.get("answer"):
                    context_parts.append(f"A{i}: {msg['answer']}")
                    
                if msg.get("preference_key"):
                    context_parts.append(f"Preference_Key: {msg['preference_key']}")
                    
                context_parts.append("")  # Spacing
        
        return "\n".join(context_parts)

    def _generate_completion_response(self, conversation: List[Dict]) -> Dict[str, Any]:
        """Generate personalized completion response"""
        answered_questions = [msg for msg in conversation if msg.get("answer")]
        
        # Build summary from actual responses
        summary_parts = []
        for msg in answered_questions[:3]:  # Show first 3 key preferences
            if msg.get("preference_key") and msg.get("answer"):
                key = msg["preference_key"].replace("_", " ").title()
                answer = msg["answer"]
                summary_parts.append(f"• {key}: {answer}")
        
        summary_text = "\n".join(summary_parts) if summary_parts else "• Your personalized preferences recorded"
        
        completion_message = f"""Perfect! I have everything needed to create your personalized meal plans.

Your Key Preferences:
{summary_text}

Based on your {len(answered_questions)} detailed responses, we'll create customized meal recommendations that match your taste, dietary needs, and lifestyle perfectly!

Ready to discover your ideal meal plans!"""
        
        return {
            "question": completion_message,
            "options": [],
            "is_complete": True,
            "preference_key": None
        }


# =============================================================================
# DYNAMIC PREFERENCE EXTRACTOR - NO STATIC CATEGORIES
# =============================================================================

class PreferenceExtractor:
    """Priority-aware preference extraction - ensures essential categories are captured"""
    
    @staticmethod
    def extract_preferences(conversation: List[Dict]) -> Dict[str, str]:
        """Extract all preferences ensuring priority categories are covered"""
        
        # Initialize with priority categories
        priority_categories = [
            "dietary_style", "spice_tolerance", "food_allergies", "regional_cuisines",
            "health_conditions", "family_needs", "cooking_constraints", 
            "meal_complexity", "fasting_observances", "general_preference"
        ]
        
        # Initialize all priority categories with default values
        preferences = {
            "dietary_style": "Any",
            "spice_tolerance": "Medium",
            "food_allergies": "None",
            "regional_cuisines": "Any",
            "health_conditions": "None",
            "family_needs": "Not specified",
            "cooking_constraints": "Flexible",
            "meal_complexity": "Simple",
            "fasting_observances": "None",
            "general_preference": "No specific preference"
        }

        logger.info(f"Extracting preferences from {len(conversation)} conversation items")
        logger.info(f"Priority categories: {priority_categories}")

        # Process each conversation item
        for item in conversation:
            try:
                preference_key = item.get("preference_key")
                answer = item.get("answer", "").strip()
                
                if not preference_key or not answer:
                    continue
                
                logger.info(f"Processing: preference_key={preference_key}, answer='{answer}'")
                
                # Clean the answer
                normalized_answer = PreferenceExtractor._normalize_answer(answer)
                
                # Store the preference
                preferences[preference_key] = normalized_answer
                
                logger.info(f"Set preference: {preference_key} = {normalized_answer}")
            
            except Exception as e:
                logger.error(f"Error processing conversation item: {str(e)}")
                continue

        logger.info(f"Final extracted preferences: {preferences}")
        return preferences
    
    @staticmethod
    def get_missing_priority_categories(conversation: List[Dict]) -> List[str]:
        """Get list of priority categories that haven't been covered yet"""
        priority_categories = [
            "dietary_style", "spice_tolerance", "food_allergies", "regional_cuisines",
            "health_conditions", "family_needs", "cooking_constraints", 
            "meal_complexity", "fasting_observances", "general_preference"
        ]
        
        covered_keys = set()
        for item in conversation:
            if item.get("preference_key") and item.get("answer"):
                covered_keys.add(item["preference_key"])
        
        missing = [cat for cat in priority_categories if cat not in covered_keys]
        logger.info(f"Missing priority categories: {missing}")
        return missing
    
    @staticmethod
    def get_coverage_status(conversation: List[Dict]) -> Dict[str, bool]:
        """Get coverage status of all priority categories"""
        priority_categories = [
            "dietary_style", "spice_tolerance", "food_allergies", "regional_cuisines",
            "health_conditions", "family_needs", "cooking_constraints", 
            "meal_complexity", "fasting_observances", "general_preference"
        ]
        
        covered_keys = set()
        for item in conversation:
            if item.get("preference_key") and item.get("answer"):
                covered_keys.add(item["preference_key"])
        
        status = {}
        for category in priority_categories:
            status[category] = category in covered_keys
        
        return status
    
    @staticmethod
    def get_completion_percentage(conversation: List[Dict]) -> float:
        """Get completion percentage of priority categories"""
        status = PreferenceExtractor.get_coverage_status(conversation)
        covered_count = sum(1 for covered in status.values() if covered)
        total_count = len(status)
        
        percentage = (covered_count / total_count) * 100
        logger.info(f"Coverage: {covered_count}/{total_count} ({percentage:.1f}%)")
        return percentage
    
    @staticmethod
    def _normalize_answer(answer: str) -> str:
        """Normalize answer - remove option prefixes and clean"""
        if not answer:
            return "Not specified"
            
        # Clean input
        answer_cleaned = answer.strip()
        
        # Remove option prefixes (A:, B:, etc.)
        if re.match(r'^[A-E][:.]', answer_cleaned, re.IGNORECASE):
            answer_cleaned = answer_cleaned[2:].strip()
        elif re.match(r'^[1-5][.)]', answer_cleaned):
            answer_cleaned = answer_cleaned[2:].strip()
        
        # Return cleaned answer
        return answer_cleaned.title() if answer_cleaned else "Not specified"

    @staticmethod
    def get_preference_summary(preferences: Dict[str, str]) -> str:
        """Generate human-readable summary of all dynamic preferences"""
        if not preferences:
            return "No preferences recorded"
        
        summary_parts = []
        for key, value in preferences.items():
            # Convert snake_case to readable format
            readable_key = key.replace("_", " ").title()
            summary_parts.append(f"• {readable_key}: {value}")
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def get_preference_categories(preferences: Dict[str, str]) -> List[str]:
        """Get list of all dynamic preference categories"""
        return list(preferences.keys())
    
    @staticmethod 
    def filter_preferences_by_pattern(preferences: Dict[str, str], pattern: str) -> Dict[str, str]:
        """Filter preferences by key pattern (e.g., 'cooking_*', 'meal_*')"""
        import re
        pattern_regex = pattern.replace("*", ".*")
        filtered = {}
        
        for key, value in preferences.items():
            if re.match(pattern_regex, key):
                filtered[key] = value
        
        return filtered


# =============================================================================
# FIXED UTILITY FUNCTIONS
# =============================================================================

import re
import logging
from fastapi import Request

logger = logging.getLogger(__name__)

def get_client_ip(request: Request) -> str:
    """Enhanced IP extraction with better error handling"""
    try:
        # Try multiple IP extraction methods
        ip_sources = [
            request.headers.get("X-Forwarded-For"),
            request.headers.get("X-Real-IP"),
            request.headers.get("CF-Connecting-IP"),  # Cloudflare
            request.headers.get("X-Client-IP"),
            getattr(request.client, 'host', None) if hasattr(request, 'client') else None
        ]
        
        for ip_source in ip_sources:
            if ip_source:
                # Handle comma-separated IPs (from proxies)
                ip_address = ip_source.split(",")[0].strip()
                if ip_address and ip_address != "unknown":
                    # Basic IPv4 validation
                    if re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip_address):
                        return ip_address
                    # IPv6 basic check
                    elif ':' in ip_address:
                        return ip_address
        
        # Fallback IP if nothing found
        fallback_ip = "127.0.0.1"
        logger.warning(f"Could not determine client IP, using fallback: {fallback_ip}")
        return fallback_ip
        
    except Exception as e:
        logger.error(f"Error retrieving client IP: {str(e)}")
        return "127.0.0.1"

def get_or_create_session(
    request: Request, 
    response: Response, 
    ip_address: str, 
    db: Session
) -> str:
    """Enhanced session management with better error handling"""
    try:
        existing_session = db.query(OnboardingSession).filter_by(
            ip_address=ip_address
        ).filter(
            OnboardingSession.expires_at > datetime.now(timezone.utc)
        ).first()

        if existing_session:
            existing_session.updated_at = datetime.now(timezone.utc)
            db.commit()
            return existing_session.session_id

        # Create new session
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

        new_session = OnboardingSession(
            session_id=session_id,
            ip_address=ip_address,
            phone_number=None,
            is_complete=False,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        logger.info(f"Created new session {session_id} for IP {ip_address}")
        return new_session.session_id

    except Exception as e:
        db.rollback()
        logger.error(f"Error in session management: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session management error: {str(e)}")


def get_onboarding_responses(db: Session, session_id: str) -> List:
    """Enhanced response fetching with error handling"""
    try:
        from api.v1.models.onboarding.onboarding_requests import OnboardingRequests
        
        responses = db.query(OnboardingRequests).filter(
            OnboardingRequests.session_id == session_id
        ).order_by(OnboardingRequests.created_at.asc()).all()
        
        logger.info(f"Retrieved {len(responses)} responses for session {session_id}")
        return responses
        
    except Exception as e:
        logger.error(f"Error fetching onboarding responses: {str(e)}")
        return []


def build_chat_history(conversation: List[Dict]) -> List:
    """Enhanced chat history building with timezone handling"""
    try:
        from api.v1.schemas.onboarding import ChatMessage
        
        chat_history = []
        ist_tz = pytz.timezone("Asia/Kolkata")
        base_time = datetime.now(ist_tz)

        for i, msg in enumerate(conversation):
            timestamp = (base_time + timedelta(seconds=i*2)).isoformat()
            
            if msg.get("question"):
                chat_history.append(ChatMessage(
                    sender="AI",
                    message=msg["question"],
                    timestamp=timestamp
                ))
            
            if msg.get("answer"):
                answer_timestamp = (base_time + timedelta(seconds=i*2 + 1)).isoformat()
                chat_history.append(ChatMessage(
                    sender="User", 
                    message=msg["answer"],
                    timestamp=answer_timestamp
                ))

        return chat_history
        
    except Exception as e:
        logger.error(f"Error building chat history: {str(e)}")
        return []


def calculate_progress(conversation: List[Dict], total_questions: int = 11) -> int:
    """FIXED: Progress calculation based on answered questions only"""
    try:
        if not total_questions or total_questions <= 0:
            total_questions = 10
        
        # Count only answered questions
        answered_count = len([msg for msg in conversation if msg.get("answer")])
        
        # Calculate progress based on answered questions
        progress = int((answered_count / total_questions) * 100)
        progress = max(0, min(progress, 100))
        
        logger.info(f"Progress calculation: {answered_count}/{total_questions} answered = {progress}%")
        return progress
        
    except Exception as e:
        logger.error(f"Error calculating progress: {str(e)}")
        return 0


def validate_user_input(user_input: str) -> Tuple[bool, str]:
    """Enhanced input validation"""
    try:
        if not user_input:
            return False, "Please provide a response"
        
        cleaned_input = user_input.strip()
        
        if len(cleaned_input) < 1:
            return False, "Response too short"
        
        if len(cleaned_input) > 500:
            return False, "Response too long (max 500 characters)"
        
        return True, "Valid input"
        
    except Exception as e:
        logger.error(f"Error validating input: {str(e)}")
        return False, "Validation error"


def is_onboarding_complete(conversation: List[Dict], min_questions: int = 10) -> bool:
    """FIXED: Completion detection - exactly 10 answered questions"""
    try:
        answered_questions = [msg for msg in conversation if msg.get("answer")]
        answered_count = len(answered_questions)
        
        logger.info(f"Completion check: {answered_count} answered questions, need {min_questions}")
        
        # Complete only when we have exactly the required number of answered questions
        return answered_count >= min_questions
        
    except Exception as e:
        logger.error(f"Error checking completion: {str(e)}")
        return False


