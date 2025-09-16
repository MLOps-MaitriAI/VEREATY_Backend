from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
import re
from api.v1.models.user.user_auth import OTP

def validate_phone_number(phone: str) -> Dict[str, Any]:
    if not phone:
        return {"valid": False, "message": "Phone number cannot be empty"}

    if not phone.startswith('+'):
        return {
            "valid": False,
            "message": "Country code is missing. Please include it (e.g., +91 for India)"
        }

    pattern = r'^\+[1-9]\d{1,14}$'
    if not re.match(pattern, phone):
        return {
            "valid": False,
            "message": "Invalid phone number."
        }

    return {"valid": True, "message": "Phone number is valid"}

def mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "*" * len(phone)
    return "*" * (len(phone) - 4) + phone[-4:]

def cleanup_expired_otps(db: Session):
    try:
        deleted_count = db.query(OTP).filter(OTP.expired_at < datetime.utcnow()).delete()
        if deleted_count > 0:
            db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error occurred")
       

def cleanup_old_otps(db: Session, phone_number: str, purpose: str):
    try:
        deleted_count = db.query(OTP).filter(
            OTP.phone_number == phone_number,
            OTP.purpose == purpose,
            OTP.is_verified == False
        ).delete()
        if deleted_count > 0:
            db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error occurred")

