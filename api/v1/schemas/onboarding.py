# =============================================================================
# PYDANTIC MODELS
# =============================================================================

from typing import Dict, List, Optional
from pydantic import BaseModel


# class UserInput(BaseModel):
#     """Model for user input during onboarding"""
#     input_type: str
#     content: str
#     language: str = "en"

# class ChatMessage(BaseModel):
#     """Model for individual chat messages"""
#     sender: str
#     message: str
#     timestamp: str

# class OnboardingResponse(BaseModel):
#     """Response model for onboarding interactions"""
#     ip_address: str
#     current_message: str
#     options: List[str] = []
#     conversation: List[ChatMessage]
#     progress: int
#     language: str
#     session_id: str
#     is_complete: bool
#     preference_key: Optional[str] = None

# class SetPreferencesResponse(BaseModel):
#     """Response model for setting user preferences"""
#     ip_address: str
#     preferences: Dict[str, str]
#     session_id: str

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

class ChatMessage(BaseModel):
    """Individual chat message in conversation"""
    sender: str = Field(..., description="Either 'AI' or 'User'")
    message: str = Field(..., description="The message content")
    timestamp: str = Field(..., description="ISO timestamp of the message")

class UserInput(BaseModel):
    """User input for onboarding response"""
    content: str = Field(..., description="User's response content")
    language: str = Field(default="en", description="Language preference")
    option_selected: Optional[str] = Field(None, description="Selected option (A, B, C, D, E)")

class OnboardingResponse(BaseModel):
    """Response from onboarding API endpoints"""
    ip_address: str = Field(..., description="Client IP address")
    current_message: str = Field(..., description="Current AI question/message")
    options: List[str] = Field(default_factory=list, description="Available response options")
    conversation: List[ChatMessage] = Field(default_factory=list, description="Full conversation history")
    progress: int = Field(default=0, description="Onboarding progress percentage (0-100)")
    language: str = Field(default="en", description="Current language")
    session_id: str = Field(..., description="Session identifier")
    is_complete: bool = Field(default=False, description="Whether onboarding is complete")
    preference_key: Optional[str] = Field(None, description="Current question's preference key")

class SetPreferencesResponse(BaseModel):
    """Response from setting user preferences"""
    ip_address: str = Field(..., description="Client IP address")
    preferences: Dict[str, str] = Field(..., description="Extracted user preferences")
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[int] = Field(None, description="Created/existing user ID")
    message: str = Field(default="Preferences saved successfully", description="Success message")

class OnboardingStatusResponse(BaseModel):
    """Response for onboarding status check"""
    session_id: str = Field(..., description="Session identifier")
    is_complete: bool = Field(..., description="Whether onboarding is complete")
    progress: int = Field(..., description="Progress percentage (0-100)")
    total_responses: int = Field(..., description="Number of questions answered")
    conversation: List[ChatMessage] = Field(..., description="Conversation history")
    created_at: datetime = Field(..., description="Session creation timestamp")
    expires_at: datetime = Field(..., description="Session expiration timestamp")

class OnboardingExportData(BaseModel):
    """Complete onboarding data export"""
    session_info: Dict[str, Any] = Field(..., description="Session metadata")
    responses: List[Dict[str, Any]] = Field(..., description="All user responses")
    extracted_preferences: Dict[str, str] = Field(..., description="Extracted preferences")
    progress: int = Field(..., description="Final progress percentage")
    total_responses: int = Field(..., description="Total number of responses")

class PreferenceUpdateRequest(BaseModel):
    """Request to update specific preferences"""
    preferences: Dict[str, str] = Field(..., description="Preferences to update")
    user_id: Optional[int] = Field(None, description="User ID if known")
    mobile_number: Optional[str] = Field(None, description="Mobile number for user identification")

class SessionResetResponse(BaseModel):
    """Response from session reset"""
    message: str = Field(..., description="Reset confirmation message")
    session_id: str = Field(..., description="Reset session ID")
    
# Additional models for comprehensive API coverage

class QuestionMetadata(BaseModel):
    """Metadata about a generated question"""
    question_key: str = Field(..., description="Unique key for the question type")
    question_text: str = Field(..., description="The actual question text")
    options: List[str] = Field(..., description="Available answer options")
    is_required: bool = Field(default=True, description="Whether this question is required")
    category: str = Field(..., description="Question category (dietary, health, etc.)")

class ConversationState(BaseModel):
    """Current state of the conversation"""
    session_id: str = Field(..., description="Session identifier")
    current_question: Optional[QuestionMetadata] = Field(None, description="Current active question")
    answered_questions: List[str] = Field(default_factory=list, description="List of answered question keys")
    pending_questions: List[str] = Field(default_factory=list, description="List of remaining question keys")
    conversation_flow: str = Field(default="dynamic", description="Type of conversation flow")

class UserPreferenceSchema(BaseModel):
    """Individual user preference item"""
    key: str = Field(..., description="Preference key")
    value: str = Field(..., description="Preference value")
    confidence_score: Optional[float] = Field(None, description="AI confidence in this preference")
    source: str = Field(..., description="How this preference was derived")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

class DetailedPreferencesResponse(BaseModel):
    """Detailed preferences with metadata"""
    user_id: Optional[int] = Field(None, description="User ID")
    session_id: str = Field(..., description="Session ID")
    preferences: List[UserPreferenceSchema] = Field(..., description="Detailed preference list")
    extraction_confidence: float = Field(..., description="Overall extraction confidence")
    missing_preferences: List[str] = Field(default_factory=list, description="Preferences that couldn't be determined")
    
class OnboardingAnalytics(BaseModel):
    """Analytics data for onboarding session"""
    session_id: str = Field(..., description="Session identifier")
    total_time_seconds: int = Field(..., description="Total time spent in onboarding")
    questions_answered: int = Field(..., description="Number of questions answered")
    questions_skipped: int = Field(..., description="Number of questions skipped")
    custom_responses: int = Field(..., description="Number of 'Other' responses requiring specification")
    completion_rate: float = Field(..., description="Completion rate as percentage")
    user_engagement_score: float = Field(..., description="Calculated engagement score")

# Request/Response models for batch operations

class BatchPreferenceUpdate(BaseModel):
    """Batch update multiple user preferences"""
    updates: List[Dict[str, Any]] = Field(..., description="List of preference updates")
    user_id: Optional[int] = Field(None, description="Target user ID")
    session_id: Optional[str] = Field(None, description="Target session ID")

class BatchUpdateResponse(BaseModel):
    """Response from batch preference update"""
    successful_updates: int = Field(..., description="Number of successful updates")
    failed_updates: int = Field(..., description="Number of failed updates")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    updated_preferences: Dict[str, str] = Field(..., description="Final preference state")

# Error response models

class OnboardingError(BaseModel):
    """Standard error response for onboarding endpoints"""
    error_code: str = Field(..., description="Specific error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

# Configuration models

class OnboardingConfig(BaseModel):
    """Configuration for onboarding process"""
    max_questions: int = Field(default=10, description="Maximum number of questions")
    min_questions: int = Field(default=5, description="Minimum questions for completion")
    session_timeout_hours: int = Field(default=24, description="Session timeout in hours")
    enable_dynamic_flow: bool = Field(default=True, description="Enable AI-driven dynamic questioning")
    fallback_questions: List[QuestionMetadata] = Field(default_factory=list, description="Fallback questions if AI fails")
    supported_languages: List[str] = Field(default_factory=lambda: ["en", "hi"], description="Supported languages")

class AIModelConfig(BaseModel):
    """Configuration for AI model used in onboarding"""
    model_name: str = Field(default="gemini-2.0-flash", description="AI model identifier")
    temperature: float = Field(default=0.7, description="Model temperature")
    max_tokens: int = Field(default=1024, description="Maximum tokens per response")
    top_p: float = Field(default=0.95, description="Top-p sampling parameter")
    top_k: int = Field(default=40, description="Top-k sampling parameter")