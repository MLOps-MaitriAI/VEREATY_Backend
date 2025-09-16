from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import pytz
import json
import os
import logging

# Third-party imports
from dotenv import load_dotenv
import google.generativeai as genai

# Local imports - Updated according to database models
from api.v1.models.onboarding.onboarding_requests import OnboardingRequests
from api.v1.models.onboarding.onboarding_sessions import OnboardingSession
from api.v1.schemas.onboarding import ChatMessage, OnboardingResponse, SetPreferencesResponse, UserInput
from db.session import get_db
from sqlalchemy.exc import SQLAlchemyError
from utils.onboarding_function import (
    DynamicConversationEngine, PreferenceExtractor, build_chat_history, 
    calculate_progress, get_client_ip, 
    get_or_create_session, 
    get_onboarding_responses 
)

router = APIRouter()
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is required but not found in environment")

genai.configure(api_key=API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize conversation engine
conversation_engine = DynamicConversationEngine()

# =============================================================================
# API ENDPOINTS - Updated for new database structure
# =============================================================================

TOTAL_QUESTIONS = 9  # Set total expected questions


TOTAL_QUESTIONS_REQUIRED = 9


@router.post("/onboarding/start", response_model=OnboardingResponse)
async def start_dynamic_onboarding(
    request: Request,
    response: Response,
    language: str = "en",
    db: Session = Depends(get_db),
    ip_address: str = Depends(get_client_ip)
):
    """Start dynamic onboarding - FIXED to require exactly 10 questions"""
    try:
        logger.info(f"Starting onboarding for IP: {ip_address}")
        
        # Get or create session
        session_id = get_or_create_session(request, response, ip_address, db)

        # Fetch existing responses
        existing_responses = get_onboarding_responses(db, session_id)
        conversation = [
            {
                "question": resp.questions, 
                "answer": resp.answer, 
                "preference_key": getattr(resp, "preference_key", None)
            }
            for resp in existing_responses
        ]

        # FIXED: Count only answered questions for completion check
        answered_questions = [msg for msg in conversation if msg.get("answer")]
        answered_count = len(answered_questions)
        
        logger.info(f"Session {session_id}: {answered_count} answered questions of {TOTAL_QUESTIONS_REQUIRED} required")

        # FIXED: Only complete when we have exactly 10 answered questions
        if answered_count >= TOTAL_QUESTIONS_REQUIRED:
            logger.info(f"Onboarding complete for session {session_id} - {answered_count} questions answered")
            
            existing_session = db.query(OnboardingSession).filter_by(session_id=session_id).first()
            if existing_session:
                existing_session.is_complete = True
                existing_session.updated_at = datetime.now(timezone.utc)
                db.commit()

            return OnboardingResponse(
                ip_address=ip_address,
                current_message="Onboarding complete! You've answered all 10 questions. Please login to proceed.",
                options=[],
                conversation=build_chat_history(conversation),
                progress=100,
                language=language,
                session_id=session_id,
                is_complete=True,
                preference_key=None
            )

        # Generate next question using FIXED conversation engine
        ai_response = conversation_engine.generate_next_question(
            conversation, user_input="", question_count=answered_count
        )

        # Check if AI determined completion (fallback safety)
        if ai_response.get("is_complete", False) and answered_count >= TOTAL_QUESTIONS_REQUIRED:
            existing_session = db.query(OnboardingSession).filter_by(session_id=session_id).first()
            if existing_session:
                existing_session.is_complete = True
                existing_session.updated_at = datetime.now(timezone.utc)
                db.commit()

            return OnboardingResponse(
                ip_address=ip_address,
                current_message="Onboarding complete! Please login to proceed.",
                options=[],
                conversation=build_chat_history(conversation),
                progress=100,
                language=language,
                session_id=session_id,
                is_complete=True,
                preference_key=None
            )

        # Save AI's question to database
        new_request = OnboardingRequests(
            session_id=session_id,
            questions=ai_response["question"],
            answer=None,
            preference_key=ai_response.get("preference_key"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        # Build response
        current_conversation = [{
            "question": ai_response["question"], 
            "answer": None, 
            "preference_key": ai_response.get("preference_key")
        }]
        chat_history = build_chat_history(conversation + current_conversation)
        
        # FIXED: Calculate progress based on answered questions
        progress = calculate_progress(conversation, TOTAL_QUESTIONS_REQUIRED)

        logger.info(f"Generated question {answered_count + 1}/{TOTAL_QUESTIONS_REQUIRED}: {ai_response['question'][:50]}...")

        return OnboardingResponse(
            ip_address=ip_address,
            current_message=ai_response["question"],
            options=ai_response.get("options", []),
            conversation=chat_history,
            progress=progress,
            language=language,
            session_id=session_id,
            is_complete=False,
            preference_key=ai_response.get("preference_key")
        )

    except HTTPException as e:
        db.rollback()
        raise e
    except SQLAlchemyError as e:
        logger.error(f"Database error in start_onboarding: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        logger.error(f"Unexpected error in start_onboarding: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Unexpected error occurred, please try again.")


@router.post("/onboarding/respond", response_model=OnboardingResponse)
async def respond_dynamic_question(
    user_input: UserInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    ip_address: str = Depends(get_client_ip)
):
    """Process user response and generate next dynamic question - FIXED for 10 questions"""
    try:
        session_id = get_or_create_session(request, response, ip_address, db)
        logger.info(f"Processing response for {ip_address}: '{user_input.content}'")

        existing_session = db.query(OnboardingSession).filter_by(session_id=session_id).first()
        
        if not existing_session:
            raise HTTPException(status_code=404, detail="Onboarding session not found")

        # Check if session is already complete
        if existing_session.is_complete:
            raise HTTPException(status_code=400, detail="Onboarding already complete! Please login to proceed.")

        # Fetch existing responses
        existing_responses = get_onboarding_responses(db, session_id)
        conversation = [
            {
                "question": resp.questions, 
                "answer": resp.answer, 
                "preference_key": getattr(resp, "preference_key", None)
            } 
            for resp in existing_responses
        ]

        # Find the last unanswered question
        last_question = db.query(OnboardingRequests).filter(
            OnboardingRequests.session_id == session_id,
            OnboardingRequests.answer.is_(None)
        ).order_by(OnboardingRequests.created_at.desc()).first()

        if not last_question:
            raise HTTPException(status_code=400, detail="No pending question found. Onboarding may be complete.")

        # Save user's answer
        last_question.answer = user_input.content
        last_question.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(last_question)

        # Update conversation with answered question
        conversation.append({
            "question": last_question.questions,
            "answer": last_question.answer,
            "preference_key": getattr(last_question, "preference_key", None)
        })

        # FIXED: Count answered questions for completion check
        answered_questions = [msg for msg in conversation if msg.get("answer")]
        answered_count = len(answered_questions)
        
        logger.info(f"Session {session_id}: {answered_count}/{TOTAL_QUESTIONS_REQUIRED} questions answered")

        # FIXED: Check completion based on answered count
        if answered_count >= TOTAL_QUESTIONS_REQUIRED:
            logger.info(f"Completing onboarding for session {session_id} - {answered_count} questions answered")
            
            existing_session.is_complete = True
            existing_session.updated_at = datetime.now(timezone.utc)
            db.commit()

            return OnboardingResponse(
                ip_address=ip_address,
                current_message=f"Perfect! Onboarding complete after {answered_count} questions. Please login to proceed.",
                options=[],
                conversation=build_chat_history(conversation),
                progress=100,
                language=user_input.language,
                session_id=session_id,
                is_complete=True,
                preference_key=None
            )

        # Generate next question using FIXED engine
        ai_response = conversation_engine.generate_next_question(
            conversation, 
            user_input.content, 
            answered_count
        )

        # Double-check AI completion decision
        if ai_response.get("is_complete", False) or answered_count >= TOTAL_QUESTIONS_REQUIRED:
            existing_session.is_complete = True
            existing_session.updated_at = datetime.now(timezone.utc)
            db.commit()

            return OnboardingResponse(
                ip_address=ip_address,
                current_message=f"Onboarding complete! You've answered {answered_count} questions. Please login to proceed.",
                options=[],
                conversation=build_chat_history(conversation),
                progress=100,
                language=user_input.language,
                session_id=session_id,
                is_complete=True,
                preference_key=None
            )

        # Save next AI question
        new_request = OnboardingRequests(
            session_id=session_id,
            questions=ai_response["question"],
            answer=None,
            preference_key=ai_response.get("preference_key"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        # Build chat history including new question
        current_conversation = [{
            "question": ai_response["question"], 
            "answer": None, 
            "preference_key": ai_response.get("preference_key")
        }]
        chat_history = build_chat_history(conversation + current_conversation)

        # FIXED: Calculate progress based on answered questions
        progress = calculate_progress(conversation, TOTAL_QUESTIONS_REQUIRED)

        logger.info(f"Generated next question {answered_count + 1}/{TOTAL_QUESTIONS_REQUIRED}: {ai_response['question'][:50]}...")

        return OnboardingResponse(
            ip_address=ip_address,
            current_message=ai_response["question"],
            options=ai_response.get("options", []),
            conversation=chat_history,
            progress=progress,
            language=user_input.language,
            session_id=session_id,
            is_complete=False,
            preference_key=ai_response.get("preference_key")
        )

    except HTTPException as e:
        db.rollback()
        raise e
    except SQLAlchemyError as e:
        logger.error(f"Database error in respond: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        logger.error(f"Unexpected error in respond: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Unexpected error occurred, please try again.")

# =========================================
# PREFERENCE API
# =========================================
@router.post("/onboarding/set-preferences", response_model=SetPreferencesResponse)
async def set_dynamic_preferences(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    ip_address: str = Depends(get_client_ip)
):
    """Extract and save user preferences from conversation history"""
    try:
        session_id = get_or_create_session(request, response, ip_address, db)
        existing_responses = get_onboarding_responses(db, session_id)

        if not existing_responses:
            raise HTTPException(status_code=404, detail="No conversation history found.")

        conversation = [
            {
                "question": r.questions, 
                "answer": r.answer, 
                "preference_key": getattr(r, "preference_key", None)
            }
            for r in existing_responses if r.answer
        ]

        # Check minimum answered questions (excluding "other" responses)
        meaningful_answers = [
            r for r in conversation 
            if r.get("answer") and "please specify" not in r.get("answer", "").lower()
        ]
        
        if len(meaningful_answers) < 5:
            raise HTTPException(
                status_code=400, 
                detail="Please answer at least 5 questions to save preferences."
            )

        # Extract preferences using the conversation
        preferences = PreferenceExtractor.extract_preferences(conversation)

        # Update session
        session = db.query(OnboardingSession).filter_by(session_id=session_id).first()
        if session:
            session.is_complete = True
            session.updated_at = datetime.now(timezone.utc)
            # Optionally store preferences as JSON if you have a preferences column
            # session.preferences = json.dumps(preferences)
            db.commit()
            db.refresh(session)

        return SetPreferencesResponse(
            ip_address=ip_address,
            preferences=preferences,
            session_id=session_id,
            user_id=None,
            message="Preferences saved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting preferences for {ip_address}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}")


# =========================================
# ADDITIONAL UTILITY ENDPOINTS
# =========================================
@router.get("/onboarding/status/{session_id}")
async def get_onboarding_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get current onboarding status for a session"""
    try:
        session = db.query(OnboardingSession).filter_by(session_id=session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        responses = get_onboarding_responses(db, session_id)
        answered_count = len([r for r in responses if r.answer])
        progress = int((answered_count / TOTAL_QUESTIONS) * 100)
        
        return {
            "session_id": session_id,
            "is_complete": session.is_complete,
            "progress": min(progress, 100),
            "questions_answered": answered_count,
            "total_questions": TOTAL_QUESTIONS
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting onboarding status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.get("/onboarding/debug/{session_id}")
async def debug_onboarding_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Debug endpoint to see conversation data and preference extraction"""
    try:
        session = db.query(OnboardingSession).filter_by(session_id=session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        responses = get_onboarding_responses(db, session_id)
        conversation = [
            {
                "question": resp.questions,
                "answer": resp.answer,
                "preference_key": getattr(resp, "preference_key", None),
                "created_at": resp.created_at.isoformat() if resp.created_at else None
            }
            for resp in responses
        ]
        
        # Extract preferences step by step for debugging
        answered_conversation = [item for item in conversation if item.get("answer")]
        preferences = PreferenceExtractor.extract_preferences(answered_conversation)
        
        return {
            "session_id": session_id,
            "session_info": {
                "ip_address": session.ip_address,
                "is_complete": session.is_complete,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            },
            "raw_conversation": conversation,
            "answered_only": answered_conversation,
            "extracted_preferences": preferences,
            "questions_total": len(conversation),
            "questions_answered": len(answered_conversation)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.delete("/onboarding/reset")
async def reset_onboarding(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    ip_address: str = Depends(get_client_ip)
):
    """Reset onboarding for current IP address"""
    try:
        # Find existing session
        existing_session = db.query(OnboardingSession).filter_by(ip_address=ip_address).first()
        
        if existing_session:
            # Delete all onboarding requests for this session
            db.query(OnboardingRequests).filter_by(session_id=existing_session.session_id).delete()
            # Delete the session
            db.delete(existing_session)
            db.commit()
            
        return {"message": "Onboarding reset successfully"}
        
    except Exception as e:
        logger.error(f"Error resetting onboarding for {ip_address}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error resetting onboarding: {str(e)}")