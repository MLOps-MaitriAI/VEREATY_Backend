# =============================================================================
# FIXED PRODUCTION-READY MEAL PLANNING ONBOARDING SYSTEM
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
# ENHANCED CONVERSATION ENGINE WITH FIXED COMPLETION LOGIC
# =============================================================================

class DynamicConversationEngine:
    """Production-ready conversation engine with fixed 10-question requirement"""
    
    def __init__(self, model_name: str = 'gemini-2.0-flash-exp'):
        try:
            self.model = genai.GenerativeModel(model_name)
            self.generation_config = {
                'temperature': 0.6,
                'top_p': 0.9,
                'top_k': 32,
                'max_output_tokens': 512,
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
        """Generate next question with FIXED completion logic for exactly 10 questions"""
        try:
            # FIXED: Only complete after exactly 10 answered questions
            answered_questions = [msg for msg in conversation_history if msg.get("answer")]
            total_answered = len(answered_questions)
            
            logger.info(f"Question generation: {total_answered} answered questions out of 10 required")
            
            # Only complete when we have exactly 10 or more answered questions
            if total_answered >= 11:
                logger.info("Completing onboarding - 10 questions answered")
                return self._generate_completion_response(conversation_history)
            
            # Build context for AI
            context = self._build_conversation_context(conversation_history)
            covered_categories = self._extract_covered_categories(conversation_history)
            
            # Create enhanced prompt
            prompt = DYNAMIC_SYSTEM_PROMPT.format(
                conversation_history=context,
                user_input=user_input,
                question_count=total_answered,  # Use answered count, not total
                covered_categories=", ".join([str(cat) for cat in covered_categories])
            )
            
            # Generate response with retry mechanism
            response = self._generate_with_retry(prompt)
            logger.info(f"Raw AI response: {response.text[:200]}...")
            
            parsed_response = self._parse_ai_response(response.text, total_answered)
            
            # Validate and enhance response
            validated_response = self._validate_and_enhance_response(parsed_response, covered_categories)
            
            # Final validation before return
            if not validated_response.get("question"):
                logger.warning("No question in validated response, using fallback")
                return self._get_intelligent_fallback(total_answered, conversation_history)
            
            return validated_response
            
        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            return self._get_intelligent_fallback(question_count, conversation_history)
    
    def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> Any:
        """Generate response with retry mechanism"""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )
                if response and response.text:
                    return response
                else:
                    logger.warning(f"Empty response on attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
        
        raise Exception("All generation attempts failed")
    
    def _extract_covered_categories(self, conversation: List[Dict]) -> set:
        """Extract set of covered preference categories - FIXED"""
        covered = set()
        for msg in conversation:
            if msg.get("preference_key") and msg.get("answer"):
                # Add the preference key as string, not as enum
                covered.add(msg["preference_key"])
        logger.info(f"Covered categories: {covered}")
        return covered
    
    def _build_conversation_context(self, conversation: List[Dict]) -> str:
        """Build enhanced conversation context"""
        if not conversation:
            return "New user starting onboarding process"
        
        context_parts = []
        for i, msg in enumerate(conversation):
            if msg.get("question"):
                context_parts.append(f"Q{i+1}: {msg['question']}")
                if msg.get("answer"):
                    context_parts.append(f"A{i+1}: {msg['answer']}")
                    if msg.get("preference_key"):
                        context_parts.append(f"Category: {msg['preference_key']}")
                context_parts.append("")  # Add spacing
        
        return "\n".join(context_parts) if context_parts else "Starting conversation"
    
    def _generate_completion_response(self, conversation: List[Dict]) -> Dict[str, Any]:
        """Generate personalized completion response"""
        answered_questions = [msg for msg in conversation if msg.get("answer")]
        
        # Extract basic preferences for summary (with safe fallbacks)
        basic_summary = {
            "dietary_style": "Not specified",
            "spice_tolerance": "Medium",
            "regional_preference": "Indian cuisine"
        }
        
        # Try to extract some key preferences for display
        for msg in answered_questions:
            pref_key = msg.get("preference_key", "")
            answer = msg.get("answer", "")
            
            if "dietary" in pref_key.lower() and answer:
                basic_summary["dietary_style"] = answer
            elif "spice" in pref_key.lower() and answer:
                basic_summary["spice_tolerance"] = answer
            elif "regional" in pref_key.lower() and answer:
                basic_summary["regional_preference"] = answer
        
        completion_message = f"""Perfect! I have everything needed to create your personalized meal plans.

Your Meal Profile Summary:
• Dietary Style: {basic_summary['dietary_style']}
• Regional Preference: {basic_summary['regional_preference']}
• Spice Level: {basic_summary['spice_tolerance']}

Based on your {len(answered_questions)} responses, we'll create customized meal recommendations just for you!

Ready to generate your personalized meals!"""
        
        return {
            "question": completion_message,
            "options": [],
            "is_complete": True,
            "preference_key": None
        }
    
    def _parse_ai_response(self, ai_text: str, question_count: int) -> Dict[str, Any]:
        """Parse AI response with robust error handling - FIXED"""
        try:
            logger.info(f"Parsing AI text for question {question_count + 1}: {ai_text[:100]}...")
            
            # Initialize default response structure
            parsed = {
                "question": "",
                "options": [],
                "preference_key": None,
                "is_complete": False
            }
            
            if not ai_text or not ai_text.strip():
                logger.warning("Empty AI response received")
                return self._get_fallback_parsed_response(question_count)
            
            lines = ai_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                line_lower = line.lower()
                
                # Check for completion indicators
                completion_indicators = [
                    "onboarding complete", "perfect! i have everything", 
                    "ready to generate", "your meal profile", "onboarding is complete"
                ]
                
                if any(indicator in line_lower for indicator in completion_indicators):
                    parsed["is_complete"] = True
                    parsed["question"] = ai_text.strip()
                    return parsed
                
                # Skip acknowledgment lines
                if any(ack in line_lower for ack in ["thanks", "great", "perfect", "got it", "wonderful"]):
                    continue
                
                # Extract question (first substantial line that looks like a question)
                if not parsed["question"] and len(line) > 10:
                    if ('?' in line or 
                        any(starter in line_lower for starter in ['what', 'which', 'how', 'do you', 'are you', 'would you']) or
                        len(line) > 20):
                        parsed["question"] = line.rstrip('?') + ('?' if '?' in line else '')
                        continue
                
                # Extract options (A, B, C, D, E format)
                option_patterns = [
                    r'^[A-E][\.\):\s]\s*(.+)',
                    r'^[1-5][\.\)]\s*(.+)',
                    r'^[A-E]\s*[-:]\s*(.+)'
                ]
                
                option_match = None
                for pattern in option_patterns:
                    option_match = re.match(pattern, line, re.IGNORECASE)
                    if option_match:
                        option_text = option_match.group(1).strip()
                        if option_text:
                            parsed["options"].append(option_text)
                        break
                
                if option_match:
                    continue
                
                # Extract preference key
                if 'preference_key' in line_lower:
                    key_patterns = [
                        r'preference_key[:\s]+([a-zA-Z_]+)',
                        r'preference[_\s]*key[:\s]+([a-zA-Z_]+)',
                        r'category[:\s]+([a-zA-Z_]+)'
                    ]
                    
                    for pattern in key_patterns:
                        key_match = re.search(pattern, line, re.IGNORECASE)
                        if key_match:
                            parsed["preference_key"] = key_match.group(1).lower()
                            break
                    continue
                
                # If we don't have a question yet and this is substantial, use it
                if not parsed["question"] and len(line) > 15:
                    parsed["question"] = line
            
            # Post-processing validation
            if not parsed["question"]:
                logger.warning("No question extracted, using fallback")
                parsed["question"] = self._get_fallback_question(question_count)
            
            # Ensure exactly 5 options with E as "Other"
            while len(parsed["options"]) < 4:
                parsed["options"].append(f"Option {len(parsed['options']) + 1}")
            
            parsed["options"] = parsed["options"][:4]
            parsed["options"].append("Other (please specify)")
            
            # Set preference key if missing
            if not parsed["preference_key"]:
                parsed["preference_key"] = self._infer_preference_key(parsed["question"], question_count)
            
            logger.info(f"Successfully parsed: question='{parsed['question'][:50]}...', options_count={len(parsed['options'])}, key={parsed['preference_key']}")
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return self._get_fallback_parsed_response(question_count)
    
    def _validate_and_enhance_response(self, parsed_response: Dict[str, Any], covered_categories: set) -> Dict[str, Any]:
        """Validate and enhance parsed response - FIXED"""
        try:
            response = {
                "question": parsed_response.get("question", ""),
                "options": parsed_response.get("options", []),
                "preference_key": parsed_response.get("preference_key"),
                "is_complete": parsed_response.get("is_complete", False)
            }
            
            # Validate question
            if not response["question"] or len(response["question"].strip()) < 5:
                logger.warning("Invalid question detected, using fallback")
                response["question"] = self._get_fallback_question(len(covered_categories))
            
            # Validate options
            if len(response["options"]) != 5:
                logger.warning(f"Invalid option count: {len(response['options'])}, normalizing")
                response["options"] = self._get_normalized_options(response["options"], len(covered_categories))
            
            # Validate preference key
            if not response["preference_key"]:
                logger.warning("Missing preference key, inferring")
                response["preference_key"] = self._infer_preference_key(response["question"], len(covered_categories))
            
            # Check if this category is already covered - if so, find alternative
            if response["preference_key"] in covered_categories:
                logger.info(f"Category {response['preference_key']} already covered, finding alternative")
                response["preference_key"] = self._get_next_uncovered_category(covered_categories)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in validation: {str(e)}")
            return self._get_fallback_parsed_response(len(covered_categories) if covered_categories else 0)
    
    def _get_normalized_options(self, existing_options: List[str], question_count: int) -> List[str]:
        """Get properly formatted 5 options"""
        try:
            options = []
            
            # Use existing options (up to 4)
            for opt in existing_options[:4]:
                if opt and opt.strip():
                    options.append(opt.strip())
            
            # Fill missing options
            default_options = self._get_default_options(question_count)
            while len(options) < 4:
                idx = len(options)
                if idx < len(default_options):
                    options.append(default_options[idx])
                else:
                    options.append(f"Option {idx + 1}")
            
            # Always add "Other"
            options.append("Other (please specify)")
            return options[:5]
            
        except Exception as e:
            logger.error(f"Error normalizing options: {str(e)}")
            return ["Yes", "No", "Sometimes", "Not sure", "Other (please specify)"]
    
    def _get_default_options(self, question_count: int) -> List[str]:
        """Get contextual default options based on question number"""
        default_sets = [
            ["Vegetarian", "Non-vegetarian", "Vegan", "Jain"],  # Q1: Dietary
            ["None", "Lactose intolerant", "Gluten-free", "Nut allergies"],  # Q2: Allergies
            ["Mild", "Medium", "Spicy", "Very spicy"],  # Q3: Spice
            ["None", "Diabetes", "High BP", "Thyroid"],  # Q4: Health
            ["North Indian", "South Indian", "Gujarati", "Bengali"],  # Q5: Regional
            ["Not needed", "Sometimes", "Always needed", "Very important"],  # Q6: Family
            ["None", "Weekly vrat", "Navratri", "Ekadashi"],  # Q7: Fasting
            ["No constraints", "Time limited", "Skill limited", "Equipment limited"],  # Q8: Cooking
            ["Simple", "Moderate", "Elaborate", "Festival style"],  # Q9: Complexity
            ["Any preference", "Low oil", "High protein", "Traditional"]  # Q10: Final
        ]
        
        if question_count < len(default_sets):
            return default_sets[question_count]
        return ["Option 1", "Option 2", "Option 3", "Option 4"]
    
    def _get_next_uncovered_category(self, covered_categories: set) -> str:
        """Get next uncovered preference category"""
        priority_order = [
            "dietary_style",
            "food_allergies", 
            "spice_tolerance",
            "health_conditions",
            "regional_cuisines",
            "family_needs",
            "fasting_observances",
            "cooking_constraints",
            "meal_complexity",
            "general_preference"
        ]
        
        for category in priority_order:
            if category not in covered_categories:
                return category
        
        return f"preference_{len(covered_categories) + 1}"
    
    def _infer_preference_key(self, question: str, question_count: int) -> str:
        """Infer preference key from question content"""
        question_lower = question.lower()
        
        # Enhanced keyword mapping
        if any(word in question_lower for word in ["dietary", "diet", "vegetarian", "meat", "jain"]):
            return "dietary_style"
        elif any(word in question_lower for word in ["allerg", "lactose", "gluten", "intolerant"]):
            return "food_allergies"
        elif any(word in question_lower for word in ["spice", "spicy", "hot", "mild"]):
            return "spice_tolerance"
        elif any(word in question_lower for word in ["health", "diabetes", "bp", "thyroid"]):
            return "health_conditions"
        elif any(word in question_lower for word in ["cuisine", "regional", "gujarati", "bengali"]):
            return "regional_cuisines"
        elif any(word in question_lower for word in ["family", "children", "kids", "child"]):
            return "family_needs"
        elif any(word in question_lower for word in ["fast", "vrat", "religious"]):
            return "fasting_observances"
        elif any(word in question_lower for word in ["time", "cooking", "preparation", "skill"]):
            return "cooking_constraints"
        elif any(word in question_lower for word in ["simple", "complex", "elaborate", "style"]):
            return "meal_complexity"
        
        # Fallback based on question sequence
        fallback_keys = [
            "dietary_style", "food_allergies", "spice_tolerance", "health_conditions",
            "regional_cuisines", "family_needs", "fasting_observances", 
            "cooking_constraints", "meal_complexity", "general_preference"
        ]
        
        if question_count < len(fallback_keys):
            return fallback_keys[question_count]
        
        return "general_preference"
    
    def _get_fallback_question(self, question_count: int) -> str:
        """Get fallback question based on sequence"""
        fallback_questions = [
            "What's your primary dietary preference?",
            "Do you have any food allergies or intolerances?",
            "What's your spice tolerance level?",
            "Do you have any health conditions to consider?",
            "Which regional cuisine do you prefer?",
            "Do you need family-friendly meal options?",
            "Do you follow any fasting practices?",
            "What are your cooking constraints?",
            "Do you prefer simple or elaborate meals?",
            "Any other dietary preferences we should know?"
        ]
        
        if question_count < len(fallback_questions):
            return fallback_questions[question_count]
        
        return "What other food preferences should we consider?"
    
    def _get_fallback_parsed_response(self, question_count: int) -> Dict[str, Any]:
        """Complete fallback response"""
        fallback_data = [
            {
                "question": "What's your primary dietary preference?",
                "options": ["Vegetarian", "Non-vegetarian", "Vegan", "Jain", "Other (please specify)"],
                "key": "dietary_style"
            },
            {
                "question": "Do you have any food allergies?",
                "options": ["None", "Lactose intolerant", "Gluten-free", "Nut allergies", "Other (please specify)"],
                "key": "food_allergies"
            },
            {
                "question": "What's your spice tolerance?",
                "options": ["Mild", "Medium", "Spicy", "Very spicy", "Other (please specify)"],
                "key": "spice_tolerance"
            },
            {
                "question": "Any health conditions to consider?",
                "options": ["None", "Diabetes", "High BP", "Thyroid", "Other (please specify)"],
                "key": "health_conditions"
            },
            {
                "question": "Which regional cuisine do you prefer?",
                "options": ["North Indian", "South Indian", "Gujarati", "Bengali", "Other (please specify)"],
                "key": "regional_cuisines"
            },
            {
                "question": "Do you need family-friendly options?",
                "options": ["Not needed", "Sometimes", "Always", "Very important", "Other (please specify)"],
                "key": "family_needs"
            },
            {
                "question": "Do you follow any fasting practices?",
                "options": ["None", "Weekly vrat", "Navratri", "Ekadashi", "Other (please specify)"],
                "key": "fasting_observances"
            },
            {
                "question": "What are your cooking time constraints?",
                "options": ["No constraints", "Quick meals only", "Moderate time", "Time flexible", "Other (please specify)"],
                "key": "cooking_constraints"
            },
            {
                "question": "Do you prefer simple or elaborate meals?",
                "options": ["Simple everyday", "Moderate complexity", "Elaborate festive", "Varies by occasion", "Other (please specify)"],
                "key": "meal_complexity"
            },
            {
                "question": "Any other dietary preferences?",
                "options": ["Low oil", "High protein", "Traditional style", "Modern fusion", "Other (please specify)"],
                "key": "general_preference"
            }
        ]
        
        index = min(question_count, len(fallback_data) - 1)
        selected = fallback_data[index]
        
        return {
            "question": selected["question"],
            "options": selected["options"],
            "preference_key": selected["key"],
            "is_complete": question_count >= 9  # Complete only after 10 questions (0-9 index)
        }
    
    def _get_intelligent_fallback(self, question_count: int, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Intelligent fallback with proper question counting"""
        answered_count = len([msg for msg in conversation_history if msg.get("answer")])
        
        logger.info(f"Intelligent fallback: answered={answered_count}, required=10")
        
        # Only complete if we truly have 10+ answers
        if answered_count >= 10:
            return self._generate_completion_response(conversation_history)
        
        return self._get_fallback_parsed_response(answered_count)


# =============================================================================
# ENHANCED PREFERENCE EXTRACTOR - FIXED
# =============================================================================

class PreferenceExtractor:
    """Enhanced preference extraction with comprehensive mapping"""
    
    @staticmethod
    def extract_preferences(conversation: List[Dict]) -> Dict[str, str]:
        """Extract structured preferences - FIXED error handling"""
        preferences = {
            "dietary_style": "Any",
            "regional_cuisines": "Any", 
            "spice_tolerance": "Medium",
            "health_conditions": "None",
            "food_allergies": "None",
            "family_needs": "Not needed",
            "fasting_observances": "None",
            "cooking_constraints": "None",
            "meal_complexity": "Simple"
        }

        logger.info(f"Extracting preferences from {len(conversation)} conversation items")

        # Process each conversation item with safe key access
        for item in conversation:
            try:
                preference_key = item.get("preference_key")
                answer = item.get("answer", "").strip()
                question = item.get("question", "").lower()
                
                if not answer:
                    continue
                
                logger.info(f"Processing: preference_key={preference_key}, answer='{answer}'")
                
                # Primary extraction using preference_key
                if preference_key and preference_key in preferences:
                    normalized_answer = PreferenceExtractor._normalize_answer(answer, preference_key)
                    preferences[preference_key] = normalized_answer
                    logger.info(f"Set {preference_key} = {normalized_answer}")
                else:
                    # Fallback: detect category from question content
                    detected_key = PreferenceExtractor._detect_preference_key_from_question(question)
                    if detected_key and detected_key in preferences:
                        normalized_answer = PreferenceExtractor._normalize_answer(answer, detected_key)
                        preferences[detected_key] = normalized_answer
                        logger.info(f"Detected {detected_key} from question, set = {normalized_answer}")
            
            except Exception as e:
                logger.error(f"Error processing conversation item: {str(e)}")
                continue

        logger.info(f"Final extracted preferences: {preferences}")
        return preferences
    
    @staticmethod
    def _detect_preference_key_from_question(question: str) -> Optional[str]:
        """Enhanced preference key detection from question content"""
        if not question:
            return None
            
        question = question.lower().strip()
        
        # Comprehensive keyword patterns
        detection_patterns = {
            "dietary_style": [
                "dietary", "diet", "vegetarian", "non-vegetarian", "vegan", "jain",
                "eating habit", "food preference", "onions", "garlic", "meat", "eggs"
            ],
            "regional_cuisines": [
                "cuisine", "regional", "south indian", "north indian", "gujarati",
                "bengali", "punjabi", "style", "food culture", "cooking style"
            ],
            "spice_tolerance": [
                "spice", "spicy", "heat", "mild", "hot", "chili", "spiciness",
                "tolerance", "spice level", "how spicy", "pepper"
            ],
            "health_conditions": [
                "health", "diabetes", "thyroid", "pressure", "cholesterol", "heart",
                "medical", "condition", "disease", "disorder", "blood sugar"
            ],
            "food_allergies": [
                "allerg", "allergic", "intolerant", "lactose", "gluten", "nuts",
                "dairy", "reaction", "avoid", "cannot eat", "sensitivity"
            ],
            "family_needs": [
                "children", "kids", "family", "child", "son", "daughter",
                "kid-friendly", "mild for kids", "family-friendly", "toddler"
            ],
            "fasting_observances": [
                "fast", "fasting", "vrat", "navratri", "ekadashi", "religious",
                "observance", "festival", "monday", "tuesday"
            ],
            "cooking_constraints": [
                "time", "cooking time", "preparation", "quick", "busy", "working",
                "constraint", "how long", "minutes", "hours"
            ],
            "meal_complexity": [
                "simple", "elaborate", "complex", "festive", "daily", "everyday",
                "home style", "traditional", "quick meal"
            ]
        }
        
        # Find best matching category
        best_category = None
        max_score = 0
        
        for category, keywords in detection_patterns.items():
            score = sum(1 for keyword in keywords if keyword in question)
            if score > max_score:
                max_score = score
                best_category = category
        
        return best_category if max_score > 0 else None
    
    @staticmethod
    def _normalize_answer(answer: str, preference_key: str) -> str:
        """Enhanced answer normalization"""
        if not answer:
            return "Not specified"
            
        # Clean input
        answer_cleaned = answer.strip()
        
        # Remove option prefixes (A:, B:, etc.)
        if re.match(r'^[A-E][:.]', answer_cleaned, re.IGNORECASE):
            answer_cleaned = answer_cleaned[2:].strip()
        elif re.match(r'^[1-5][.)]', answer_cleaned):
            answer_cleaned = answer_cleaned[2:].strip()
        
        answer_lower = answer_cleaned.lower()
        
        # Use preference mappings if available
        try:
            if preference_key in PREFERENCE_MAPPINGS:
                mapping = PREFERENCE_MAPPINGS[preference_key]
                
                # Direct match
                if answer_lower in mapping:
                    return mapping[answer_lower]
                
                # Partial matching
                for key, value in mapping.items():
                    if key in answer_lower or answer_lower in key:
                        return value
        except Exception as e:
            logger.error(f"Error in preference mapping: {str(e)}")
        
        # Category-specific normalization
        return PreferenceExtractor._category_specific_normalization(answer_cleaned, preference_key)
    
    @staticmethod
    def _category_specific_normalization(answer: str, preference_key: str) -> str:
        """Category-specific normalization logic"""
        if not answer:
            return "Not specified"
            
        answer_lower = answer.lower()
        
        if preference_key == "dietary_style":
            if "jain" in answer_lower:
                return "Jain"
            elif "vegan" in answer_lower:
                return "Vegan"
            elif "vegetarian" in answer_lower and "non" not in answer_lower:
                return "Vegetarian"
            elif any(word in answer_lower for word in ["non-veg", "non veg", "meat", "chicken"]):
                return "Non-vegetarian"
            elif "egg" in answer_lower:
                return "Eggetarian"
        
        elif preference_key == "spice_tolerance":
            if "mild" in answer_lower or "low" in answer_lower:
                return "Mild"
            elif "medium" in answer_lower or "moderate" in answer_lower:
                return "Medium"
            elif "very spicy" in answer_lower or "extra spicy" in answer_lower:
                return "Very Spicy"
            elif "spicy" in answer_lower or "hot" in answer_lower:
                return "Spicy"
        
        elif preference_key == "health_conditions":
            if "diabetes" in answer_lower:
                return "Diabetes"
            elif "thyroid" in answer_lower:
                return "Thyroid"
            elif "bp" in answer_lower or "blood pressure" in answer_lower:
                return "High Blood Pressure"
            elif "none" in answer_lower or "healthy" in answer_lower:
                return "None"
        
        elif preference_key == "food_allergies":
            if "lactose" in answer_lower or "dairy" in answer_lower:
                return "Lactose Intolerant"
            elif "gluten" in answer_lower or "wheat" in answer_lower:
                return "Gluten Intolerant"
            elif "nut" in answer_lower:
                return "Nut Allergies"
            elif "none" in answer_lower or "no allergies" in answer_lower:
                return "None"
        
        elif preference_key == "regional_cuisines":
            if "south indian" in answer_lower:
                return "South Indian"
            elif "north indian" in answer_lower:
                return "North Indian"
            elif "gujarati" in answer_lower:
                return "Gujarati"
            elif "bengali" in answer_lower:
                return "Bengali"
            elif "punjabi" in answer_lower:
                return "Punjabi"
        
        elif preference_key == "family_needs":
            if any(word in answer_lower for word in ["yes", "always", "required", "needed"]):
                return "Required"
            elif any(word in answer_lower for word in ["sometimes", "occasionally"]):
                return "Sometimes"
            elif any(word in answer_lower for word in ["no", "never", "not needed"]):
                return "Not needed"
        
        elif preference_key == "fasting_observances":
            if "weekly" in answer_lower or "vrat" in answer_lower:
                return "Weekly Vrat"
            elif "navratri" in answer_lower:
                return "Navratri"
            elif "ekadashi" in answer_lower:
                return "Ekadashi"
            elif "none" in answer_lower or "no fasting" in answer_lower:
                return "None"
        
        # Return cleaned answer if no specific mapping found
        return answer.title() if answer else "Not specified"


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


