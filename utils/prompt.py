# # =============================================================================
# # PRODUCTION-READY MEAL PLANNING ONBOARDING SYSTEM
# # =============================================================================

from enum import Enum


DYNAMIC_SYSTEM_PROMPT = """
You are Vereaty's AI Meal Planning Assistant, designed to conduct intelligent, adaptive onboarding interviews for Indian users.

CORE MISSION:
Collect comprehensive dietary preferences through 10-15 contextually adaptive questions that build upon previous responses to create highly personalized meal recommendations.

CONVERSATION PROTOCOL:
- Opening: "Hi! Let's create your perfect meal plan with a few quick questions."
- ONE focused question per interaction (maximum 18 words)
- EXACTLY 5 options (A, B, C, D, E) where E is ALWAYS "Other (please specify)"
- Brief acknowledgments: "Got it!" or "Perfect!" (max 2 words)
- Maintain natural, conversational flow with intelligent branching

INTELLIGENT BRANCHING SYSTEM:
Questions must adapt dynamically based on user responses:

DIETARY FOUNDATION FLOW:
- Primary dietary style → Specific dietary nuances
- If "Jain" → "Do you avoid all root vegetables including onions and garlic?"
- If "Non-vegetarian" → "Which proteins do you prefer most?"
- If "Diabetic" → "Do you need completely sugar-free meals?"
- If "Has children" → "Should meals be mild and kid-friendly?"

REGIONAL CUISINE FLOW:
- South Indian → "Do you prefer rice-based meals daily?"
- Gujarati → "Do you enjoy sweet flavors in main dishes?"
- Punjabi → "Do you like rich, creamy preparations?"
- Bengali → "Are fish dishes important in your meals?"

HEALTH-CONSCIOUS FLOW:
- Diabetes → Sugar management preferences
- High BP → Sodium restriction needs
- Thyroid → Metabolic dietary considerations
- Weight management → Portion and ingredient preferences

ESSENTIAL PREFERENCE CATEGORIES (Cover 10-15):
✓ dietary_style: vegetarian, jain, vegan, non_vegetarian, eggetarian
✓ regional_cuisines: north_indian, south_indian, gujarati, bengali, punjabi
✓ spice_tolerance: mild, medium, spicy, very_spicy
✓ health_conditions: diabetes, thyroid, hypertension, none
✓ food_allergies: lactose, gluten, nuts, none
✓ family_needs: kid_friendly_required, sometimes, not_needed
✓ fasting_observances: weekly_vrat, navratri, ekadashi, none
✓ cooking_constraints: time_limited, ingredient_limited, skill_limited, none
✓ meal_complexity: simple_homestyle, elaborate_festive, quick_everyday

RESPONSE FORMATTING RULES:
- Questions must be SHORT and SPECIFIC
- ✓ "Which proteins do you eat regularly?"
- ✗ "Could you tell me about your protein consumption patterns and dietary habits?"

- ✓ "Do you need diabetic-friendly meal options?"
- ✗ "Given your health condition, what specific dietary modifications would you prefer for managing your health effectively?"

Always conclude with: preference_key: [category_name]

COMPLETION CRITERIA:
After collecting 10-15 adaptive responses covering essential categories:

"Perfect! I have everything needed to create your personalized meal plans.

Your Meal Profile:
• Dietary Style: {dietary_style}
• Regional Preference: {regional_cuisines}
• Spice Level: {spice_tolerance}
• Health Considerations: {health_conditions}
• Special Requirements: {food_allergies}, {family_needs}

Ready to generate your customized meals!"

CONTEXT VARIABLES:
- Previous conversation: {conversation_history}
- Latest user response: {user_input}
- Question count: {question_count}
- Categories covered: {covered_categories}

Generate the next contextually appropriate question with intelligent branching logic, or provide completion summary if sufficient comprehensive data is collected.

CRITICAL PRODUCTION RULES:
- Zero question overlap or repetition
- Each question builds logically on previous answers
- Natural conversation flow with contextual relevance
- Focus on actionable dietary preferences
- Include preference_key in every response for data structure
- Maintain professional, helpful tone throughout
"""

# =============================================================================
# COMPREHENSIVE PREFERENCE MAPPINGS
# =============================================================================

class PreferenceCategory(str, Enum):
    """Enumeration of all preference categories"""
    DIETARY_STYLE = "dietary_style"
    REGIONAL_CUISINES = "regional_cuisines"
    SPICE_TOLERANCE = "spice_tolerance"
    HEALTH_CONDITIONS = "health_conditions"
    FOOD_ALLERGIES = "food_allergies"
    FAMILY_NEEDS = "family_needs"
    FASTING_OBSERVANCES = "fasting_observances"
    COOKING_CONSTRAINTS = "cooking_constraints"
    MEAL_COMPLEXITY = "meal_complexity"

# Enhanced preference mappings with comprehensive vocabulary coverage
PREFERENCE_MAPPINGS = {
    PreferenceCategory.DIETARY_STYLE: {
        # Vegetarian variants
        "vegetarian": "vegetarian",
        "veg": "vegetarian",
        "pure_veg": "vegetarian",
        "lacto_vegetarian": "vegetarian",
        "strict_vegetarian": "vegetarian",
        
        # Jain specific
        "jain": "jain",
        "jain_vegetarian": "jain",
        "no_root_vegetables": "jain",
        "avoid_onion_garlic": "jain",
        
        # Vegan
        "vegan": "vegan",
        "plant_based": "vegan",
        "no_dairy": "vegan",
        "no_animal_products": "vegan",
        
        # Non-vegetarian
        "non_vegetarian": "non_vegetarian",
        "non_veg": "non_vegetarian",
        "meat_eater": "non_vegetarian",
        "omnivore": "non_vegetarian",
        
        # Eggetarian
        "eggetarian": "eggetarian",
        "egg_vegetarian": "eggetarian",
        "vegetarian_with_eggs": "eggetarian",
        
        # Pescatarian
        "pescatarian": "pescatarian",
        "fish_only": "pescatarian",
        "vegetarian_with_fish": "pescatarian",
    },
    
    PreferenceCategory.REGIONAL_CUISINES: {
        # North Indian variations
        "north_indian": "north_indian",
        "punjabi": "north_indian",
        "delhi_style": "north_indian",
        "uttar_pradesh": "north_indian",
        "haryanvi": "north_indian",
        "himachali": "north_indian",
        
        # South Indian variations
        "south_indian": "south_indian",
        "tamil": "south_indian",
        "tamil_nadu": "south_indian",
        "kerala": "south_indian",
        "andhra": "south_indian",
        "telugu": "south_indian",
        "karnataka": "south_indian",
        "kannada": "south_indian",
        
        # Gujarati variations
        "gujarati": "gujarati",
        "gujju": "gujarati",
        "kathiawadi": "gujarati",
        "surti": "gujarati",
        
        # Bengali variations
        "bengali": "bengali",
        "west_bengal": "bengali",
        "kolkata_style": "bengali",
        "assamese": "bengali",
        
        # Other major cuisines
        "maharashtrian": "maharashtrian",
        "marathi": "maharashtrian",
        "mumbai_style": "maharashtrian",
        "rajasthani": "rajasthani",
        "marwari": "rajasthani",
        "bihari": "bihari",
        "odia": "odia",
        "kashmiri": "kashmiri",
        
        # Mixed preferences
        "all_indian": "all_indian",
        "mixed_regional": "all_indian",
        "variety": "all_indian",
    },
    
    PreferenceCategory.SPICE_TOLERANCE: {
        "mild": "mild",
        "low_spice": "mild",
        "light_spice": "mild",
        "kids_level": "mild",
        "no_spice": "mild",
        
        "medium": "medium",
        "moderate": "medium",
        "normal_spice": "medium",
        "average_indian": "medium",
        
        "spicy": "spicy",
        "high_spice": "spicy",
        "hot": "spicy",
        "indian_level": "spicy",
        
        "very_spicy": "very_spicy",
        "extra_spicy": "very_spicy",
        "extremely_hot": "very_spicy",
        "maximum_spice": "very_spicy",
    },
    
    PreferenceCategory.HEALTH_CONDITIONS: {
        "none": "none",
        "healthy": "none",
        "no_issues": "none",
        "all_good": "none",
        
        "diabetes": "diabetes",
        "diabetic": "diabetes",
        "type_2_diabetes": "diabetes",
        "blood_sugar": "diabetes",
        "sugar_problem": "diabetes",
        
        "hypertension": "hypertension",
        "high_blood_pressure": "hypertension",
        "high_bp": "hypertension",
        "bp_problem": "hypertension",
        
        "thyroid": "thyroid",
        "hypothyroid": "thyroid",
        "hyperthyroid": "thyroid",
        "thyroid_disorder": "thyroid",
        
        "heart_disease": "heart_disease",
        "cardiac_issue": "heart_disease",
        "heart_problem": "heart_disease",
        
        "cholesterol": "cholesterol",
        "high_cholesterol": "cholesterol",
        "lipid_disorder": "cholesterol",
        
        "obesity": "weight_management",
        "overweight": "weight_management",
        "weight_loss_needed": "weight_management",
        
        "pcod": "hormonal_disorder",
        "pcos": "hormonal_disorder",
        "hormonal_imbalance": "hormonal_disorder",
    },
    
    PreferenceCategory.FOOD_ALLERGIES: {
        "none": "none",
        "no_allergies": "none",
        "nothing": "none",
        
        "lactose_intolerant": "lactose",
        "dairy_allergy": "lactose",
        "milk_allergy": "lactose",
        "no_dairy": "lactose",
        
        "gluten_intolerant": "gluten",
        "gluten_allergy": "gluten",
        "wheat_allergy": "gluten",
        "celiac": "gluten",
        
        "nut_allergies": "nuts",
        "tree_nuts": "nuts",
        "peanut_allergy": "nuts",
        "almond_allergy": "nuts",
        
        "shellfish_allergy": "shellfish",
        "seafood_allergy": "shellfish",
        "fish_allergy": "shellfish",
        
        "egg_allergy": "eggs",
        "egg_intolerant": "eggs",
        
        "soy_allergy": "soy",
        "soybean_allergy": "soy",
    },
    
    PreferenceCategory.FAMILY_NEEDS: {
        "kid_friendly_required": "required",
        "always_kid_friendly": "required",
        "must_be_mild": "required",
        "children_first": "required",
        
        "sometimes_needed": "sometimes",
        "occasionally": "sometimes",
        "depends": "sometimes",
        
        "not_needed": "not_needed",
        "no_children": "not_needed",
        "adults_only": "not_needed",
        "never": "not_needed",
    },
    
    PreferenceCategory.FASTING_OBSERVANCES: {
        "none": "none",
        "no_fasting": "none",
        "never_fast": "none",
        
        "weekly_vrat": "weekly_vrat",
        "monday_fast": "weekly_vrat",
        "tuesday_fast": "weekly_vrat",
        "thursday_fast": "weekly_vrat",
        "saturday_fast": "weekly_vrat",
        
        "navratri": "navratri",
        "navratri_fasting": "navratri",
        "durga_puja": "navratri",
        
        "ekadashi": "ekadashi",
        "ekadashi_vrat": "ekadashi",
        
        "karva_chauth": "karva_chauth",
        "festival_fasts": "festival_fasts",
        "occasional_fasting": "occasional_fasting",
        
        "multiple_fasts": "multiple",
        "various_fasts": "multiple",
    },
}


# # Core system prompt for dynamic conversational onboarding
# DYNAMIC_SYSTEM_PROMPT = """
# You are Vereaty's AI Meal Planning Assistant. Your role is to conduct an intelligent, adaptive interview to understand each user's unique food preferences and dietary requirements.

# MISSION:
# Collect comprehensive user preferences through 8-12 contextual questions that adapt based on previous responses, ensuring personalized meal planning recommendations.

# CONVERSATION FRAMEWORK:
# - Opening: "Hi! I'm here to create your perfect meal plan. Let's start with a few quick questions."
# - ONE question per interaction (maximum 15 words)
# - EXACTLY 5 options (A, B, C, D, E) where E is always "Other (please specify)"
# - Brief acknowledgments: "Got it!" or "Perfect!"
# - Natural conversation flow with intelligent branching

# ADAPTIVE QUESTIONING LOGIC:
# Your questions must intelligently branch based on user responses:

# DIETARY FOUNDATION:
# - Start with core dietary style
# - If "Jain" → Ask about root vegetables (onions/garlic)
# - If "Vegan" → Ask about plant protein preferences
# - If "Non-vegetarian" → Ask about protein types
# - If "Vegetarian" → Ask about dairy/egg consumption

# HEALTH & LIFESTYLE:
# - If health conditions mentioned → Ask about dietary restrictions
# - If children mentioned → Ask about kid-friendly requirements
# - If allergies mentioned → Ask about severity levels
# - If regional cuisine mentioned → Ask about spice preferences

# CONTEXTUAL FOLLOW-UPS:
# - Diabetes → "Do you need sugar-free meal options?"
# - South Indian → "Do you prefer rice-based meals daily?"
# - Punjabi → "Do you enjoy rich, creamy dishes regularly?"
# - Children: Yes → "Should meals be mild and kid-friendly?"

# PREFERENCE CATEGORIES (Cover 6-8 essential ones):
# ✓ dietary_style: vegetarian, vegan, jain, non_vegetarian, eggetarian
# ✓ regional_cuisines: north_indian, south_indian, gujarati, bengali, punjabi
# ✓ spice_level: mild, medium, spicy, very_spicy
# ✓ allergies: lactose, gluten, nuts, shellfish, none
# ✓ health_concerns: diabetes, thyroid, bp, heart, none
# ✓ children_needs: kid_friendly_always, sometimes, never
# ✓ fasting_practices: weekly_vrat, navratri, ekadashi, none
# ✓ protein_preferences: chicken, fish, eggs, mutton, vegetarian_only

# RESPONSE FORMAT:
# Keep questions SHORT and SPECIFIC:
# ✓ "Which proteins do you eat most?"
# ✗ "Could you tell me about your protein consumption habits and preferences?"

# ✓ "Do you need diabetic-friendly meals?"
# ✗ "Given your health condition, what dietary modifications would you prefer?"

# Always end with: preference_key: [category_name]

# COMPLETION CRITERIA:
# After 8-12 adaptive questions covering essential categories:
# "Perfect! I have everything needed to create your personalized meal plans.

# Your Profile Summary:
# • Dietary Style: {dietary_style}
# • Regional Preference: {regional_cuisines}
# • Spice Level: {spice_level}
# • Special Requirements: {health_concerns}, {allergies}

# You're all set to start generating customized meals!"

# CONVERSATION CONTEXT:
# Previous responses: {conversation_history}
# Current input: {user_input}
# Questions asked: {question_count}
# Categories covered: {covered_categories}

# Generate the next contextually appropriate question with proper branching logic, or provide completion summary if sufficient data is collected.

# CRITICAL RULES:
# - No repetitive or overlapping questions
# - Each question must build on previous answers
# - Maintain natural conversation flow
# - Focus on most relevant categories first
# - Include preference_key in every response
# """

# # Comprehensive preference mapping for structured data extraction
# PREFERENCE_MAPPINGS = {
#     "dietary_style": {
#         # Primary categories
#         "vegetarian": "vegetarian",
#         "veg": "vegetarian", 
#         "pure_veg": "vegetarian",
#         "jain": "jain",
#         "jain_vegetarian": "jain",
#         "vegan": "vegan",
#         "plant_based": "vegan",
#         "non_vegetarian": "non_vegetarian",
#         "non_veg": "non_vegetarian",
#         "meat_eater": "non_vegetarian",
#         "eggetarian": "eggetarian",
#         "egg_vegetarian": "eggetarian",
#         "lacto_vegetarian": "lacto_vegetarian",
#         "pescatarian": "pescatarian",
#         "fish_only": "pescatarian"
#     },
    
#     "regional_cuisines": {
#         # Major regional preferences
#         "north_indian": "north_indian",
#         "punjabi": "north_indian",
#         "delhi": "north_indian",
#         "uttar_pradesh": "north_indian",
#         "south_indian": "south_indian", 
#         "tamil": "south_indian",
#         "kerala": "south_indian",
#         "andhra": "south_indian",
#         "karnataka": "south_indian",
#         "gujarati": "gujarati",
#         "gujju": "gujarati",
#         "kathiawadi": "gujarati",
#         "bengali": "bengali",
#         "kolkata": "bengali",
#         "west_bengal": "bengali",
#         "maharashtrian": "maharashtrian",
#         "marathi": "maharashtrian",
#         "mumbai": "maharashtrian",
#         "rajasthani": "rajasthani",
#         "marwari": "rajasthani",
#         "all_indian": "all_indian",
#         "mixed": "all_indian"
#     },
    
#     "spice_level": {
#         "mild": "mild",
#         "low_spice": "mild",
#         "light": "mild",
#         "kids_level": "mild",
#         "medium": "medium",
#         "moderate": "medium", 
#         "normal": "medium",
#         "average": "medium",
#         "spicy": "spicy",
#         "hot": "spicy",
#         "high": "spicy",
#         "very_spicy": "very_spicy",
#         "extra_spicy": "very_spicy",
#         "extremely_hot": "very_spicy",
#         "indian_spicy": "very_spicy"
#     },
    
#     "allergies": {
#         "none": "none",
#         "no_allergies": "none",
#         "lactose_intolerant": "lactose",
#         "dairy_free": "lactose",
#         "milk_allergy": "lactose",
#         "gluten_intolerant": "gluten",
#         "gluten_free": "gluten",
#         "wheat_allergy": "gluten",
#         "nut_allergies": "nuts",
#         "tree_nuts": "nuts",
#         "peanut_allergy": "nuts",
#         "shellfish_allergy": "shellfish",
#         "seafood_allergy": "shellfish",
#         "egg_allergy": "eggs",
#         "soy_allergy": "soy"
#     },
    
#     "health_concerns": {
#         "none": "none",
#         "healthy": "none",
#         "diabetes": "diabetes",
#         "diabetic": "diabetes",
#         "blood_sugar": "diabetes",
#         "thyroid": "thyroid",
#         "hyperthyroid": "thyroid",
#         "hypothyroid": "thyroid",
#         "high_bp": "high_bp",
#         "hypertension": "high_bp",
#         "blood_pressure": "high_bp",
#         "heart_disease": "heart_disease",
#         "cardiac": "heart_disease",
#         "cholesterol": "cholesterol",
#         "high_cholesterol": "cholesterol",
#         "obesity": "weight_management",
#         "weight_loss": "weight_management",
#         "pcod": "pcod",
#         "pcos": "pcod"
#     },
    
#     "children_needs": {
#         "kid_friendly_always": "always",
#         "always": "always",
#         "yes_always": "always",
#         "sometimes": "sometimes", 
#         "occasionally": "sometimes",
#         "rarely": "rarely",
#         "seldom": "rarely",
#         "never": "never",
#         "no_kids": "never",
#         "not_needed": "never"
#     },
    
#     "fasting_practices": {
#         "none": "none",
#         "no_fasting": "none",
#         "weekly_vrat": "weekly_vrat",
#         "monday_fast": "weekly_vrat",
#         "tuesday_fast": "weekly_vrat", 
#         "navratri": "navratri",
#         "ekadashi": "ekadashi",
#         "karva_chauth": "karva_chauth",
#         "janmashtami": "festival_fasts",
#         "mahashivratri": "festival_fasts",
#         "multiple": "multiple"
#     },
    
#     "protein_preferences": {
#         "chicken": "chicken",
#         "fish": "fish",
#         "seafood": "fish",
#         "eggs": "eggs",
#         "mutton": "mutton",
#         "lamb": "mutton",
#         "goat": "mutton",
#         "all_non_veg": "all_non_veg",
#         "vegetarian_only": "vegetarian_only",
#         "paneer": "vegetarian_only",
#         "dal": "vegetarian_only"
#     }
# }

# # Intelligent question flow system
# class QuestionFlow:
#     """Manages dynamic question generation based on conversation context"""
    
#     ESSENTIAL_CATEGORIES = [
#         "dietary_style",
#         "regional_cuisines", 
#         "spice_level",
#         "allergies"
#     ]
    
#     CONDITIONAL_CATEGORIES = {
#         "health_concerns": lambda prefs: True,  # Always relevant
#         "children_needs": lambda prefs: prefs.get("household_type") == "family",
#         "fasting_practices": lambda prefs: prefs.get("dietary_style") in ["vegetarian", "jain"],
#         "protein_preferences": lambda prefs: prefs.get("dietary_style") == "non_vegetarian"
#     }
    
#     @classmethod
#     def get_next_category(cls, covered_categories, user_preferences):
#         """Determine next category to ask about based on context"""
        
#         # First, cover essential categories
#         for category in cls.ESSENTIAL_CATEGORIES:
#             if category not in covered_categories:
#                 return category
        
#         # Then, ask conditional categories based on previous answers
#         for category, condition in cls.CONDITIONAL_CATEGORIES.items():
#             if category not in covered_categories and condition(user_preferences):
#                 return category
                
#         return None

# # Contextual question templates
# CONTEXTUAL_QUESTIONS = {
#     "dietary_style": {
#         "question": "What's your dietary preference?",
#         "options": [
#             "A: Vegetarian",
#             "B: Non-vegetarian",
#             "C: Jain (no root vegetables)",
#             "D: Vegan",
#             "E: Other (please specify)"
#         ]
#     },
    
#     "regional_cuisines": {
#         "question": "Which cuisine do you enjoy most?",
#         "options": [
#             "A: North Indian",
#             "B: South Indian", 
#             "C: Gujarati",
#             "D: Bengali",
#             "E: Other (please specify)"
#         ]
#     },
    
#     "spice_level": {
#         "question": "How spicy do you like your food?",
#         "options": [
#             "A: Mild",
#             "B: Medium",
#             "C: Spicy",
#             "D: Very spicy",
#             "E: Other (please specify)"
#         ]
#     },
    
#     "allergies": {
#         "question": "Do you have any food allergies?",
#         "options": [
#             "A: None",
#             "B: Lactose intolerant",
#             "C: Gluten-free needed",
#             "D: Nut allergies",
#             "E: Other (please specify)"
#         ]
#     }
# }

# # Adaptive follow-up questions based on previous answers
# ADAPTIVE_QUESTIONS = {
#     "dietary_style": {
#         "jain": {
#             "question": "Do you avoid onions and garlic completely?",
#             "options": [
#                 "A: Yes, completely avoid",
#                 "B: Avoid in main meals only",
#                 "C: Sometimes okay",
#                 "D: Only avoid onions",
#                 "E: Other (please specify)"
#             ],
#             "preference_key": "jain_strictness"
#         },
#         "non_vegetarian": {
#             "question": "Which proteins do you eat most?",
#             "options": [
#                 "A: Chicken",
#                 "B: Fish and seafood", 
#                 "C: Mutton/lamb",
#                 "D: All types",
#                 "E: Other (please specify)"
#             ],
#             "preference_key": "protein_preferences"
#         },
#         "vegan": {
#             "question": "Do you eat processed vegan alternatives?",
#             "options": [
#                 "A: Yes, regularly",
#                 "B: Sometimes",
#                 "C: Prefer whole foods only",
#                 "D: Only homemade",
#                 "E: Other (please specify)"
#             ],
#             "preference_key": "vegan_style"
#         }
#     },
    
#     "health_concerns": {
#         "diabetes": {
#             "question": "Do you need sugar-free meal options?",
#             "options": [
#                 "A: Yes, completely sugar-free",
#                 "B: Low sugar preferred",
#                 "C: Natural sweeteners okay",
#                 "D: Controlled portions",
#                 "E: Other (please specify)"
#             ],
#             "preference_key": "diabetes_management"
#         }
#     },
    
#     "regional_cuisines": {
#         "south_indian": {
#             "question": "Do you prefer rice-based meals daily?",
#             "options": [
#                 "A: Yes, rice with every meal",
#                 "B: Rice for lunch/dinner only",
#                 "C: Mix of rice and roti",
#                 "D: Prefer roti more",
#                 "E: Other (please specify)"
#             ],
#             "preference_key": "grain_preference"
#         }
#     }
# }

# # Configuration constants
# class Config:
#     MIN_QUESTIONS = 8
#     MAX_QUESTIONS = 12
#     COMPLETION_THRESHOLD = 9  # Minimum categories to complete onboarding
    
#     GREETING = "Hi! I'm here to create your perfect meal plan. Let's start with a few quick questions."
    
#     COMPLETION_TEMPLATE = """Perfect! I have everything needed to create your personalized meal plans.

# Your Profile Summary:
# • Dietary Style: {dietary_style}
# • Regional Preference: {regional_cuisines} 
# • Spice Level: {spice_level}
# • Special Requirements: {special_requirements}

# You're all set to start generating customized meals!"""

# # Validation and error handling
# class ValidationRules:
#     """Validation rules for user responses"""
    
#     @staticmethod
#     def validate_response(response, category):
#         """Validate user response format and content"""
#         if not response or len(response.strip()) == 0:
#             return False, "Please provide a response"
        
#         if response.upper() in ['A', 'B', 'C', 'D']:
#             return True, "Valid option selected"
        
#         if response.upper().startswith('E'):
#             if len(response) < 3:
#                 return False, "Please specify your preference after selecting E"
#             return True, "Custom response provided"
        
#         return True, "Free text response accepted"

# # Production-ready error messages
# ERROR_MESSAGES = {
#     "invalid_response": "I didn't understand that. Please choose A, B, C, D, or E with your specification.",
#     "incomplete_response": "Could you please provide more details?",
#     "system_error": "I'm having trouble processing that. Could you try again?",
#     "timeout_error": "Let's continue with a quick question to keep things moving."
# }

# # Success completion messages
# SUCCESS_MESSAGES = [
#     "Excellent! Your meal preferences are now saved.",
#     "Perfect! I have all the details needed for your personalized meals.",
#     "Great! Your custom meal profile is ready.",
#     "Wonderful! Let's start creating meals just for you."
# ]