from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError
from api.v1.models.onboarding.onboarding_sessions import OnboardingSession
from api.v1.models.user.user_auth import OTP, User
from api.v1.schemas.user import StatusEnum, UserType, UserUpdateRequest
from auth.auth_handler import signJWT
from core.phone_config import send_otp_sms
from db.session import get_db
import random
import re
import logging
from fastapi import Request, Response
from sqlalchemy.sql.expression import desc
# from api.v1.models.user.user_auth import UserOut
from utils.onboarding_function import get_or_create_session
from utils.validators import cleanup_expired_otps, cleanup_old_otps, mask_phone, validate_phone_number

router = APIRouter()


def generate_otp():
    return str(random.randint(1000, 9999))

@router.post("/v1/auth/register")
def register(phone_number: str ,request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        
        if not validate_phone_number(phone_number)["valid"]:
            raise HTTPException(status_code=422, detail="Invalid phone number.")
        
        existing_user = db.query(User).filter(User.phone_number == phone_number).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered.")
        
        ip_address = request.client.host if request.client else "unknown"
        session_id = get_or_create_session(request, response, ip_address, db)

        if not session_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="complete onboarding first before registration.")
        
        onboarding_db=db.query(OnboardingSession).filter(OnboardingSession.ip_address==ip_address).first()
        if onboarding_db:
            onboarding_db.phone_number=phone_number
            db.commit()

        new_user = User(
            session_id=session_id,
            ip_address=ip_address,
            username=None,
            email=None,
            phone_number=phone_number, 
            status=StatusEnum.pending_verification,
            user_type= UserType.user,
            created_at=datetime.now(timezone.utc),
            is_verified=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Generate OTP
        otp_code = generate_otp()
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=5)

        otp_entry = OTP(
            phone_number=phone_number,  
            purpose="register",
            otp_code=otp_code,
            attempt_count=0,
            status="active",
            is_verified=False,
            generated_at=now,
            expired_at=expiry
        )
        db.add(otp_entry)
        db.commit()

        if not send_otp_sms(phone_number, otp_code):  
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to send OTP.")

        return {
            "message": "User created successfully. OTP sent for verification.",
            "phone_number": new_user.phone_number,
            "user_id": new_user.user_id
        }

    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error occurred during registration.{e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during registration.{e}")

@router.post("/v1/auth/verify-register_otp")
def verify_register_otp(phone_number: str, otp_code: str, db: Session = Depends(get_db)):
    try:
        now = datetime.now(timezone.utc)  
        max_attempts = 5

        if not validate_phone_number(phone_number)["valid"]:
            raise HTTPException(status_code=422, detail="Invalid phone number.")

        user_db = db.query(User).filter(User.phone_number == phone_number).first()
        if not user_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        otp_entry = db.query(OTP).filter(
            OTP.phone_number == phone_number,
            OTP.purpose == "register",
            OTP.is_verified == False,
            OTP.status == "active"
        ).order_by(desc(OTP.generated_at)).first()

        if not otp_entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active OTP found.")

        otp_generated_at = otp_entry.generated_at
        if otp_generated_at.tzinfo is None:
            otp_generated_at = otp_generated_at.replace(tzinfo=timezone.utc)

        otp_expired_at = otp_entry.expired_at
        if otp_expired_at.tzinfo is None:
            otp_expired_at = otp_expired_at.replace(tzinfo=timezone.utc)

        if now > otp_expired_at:
            otp_entry.status = "expired"
            otp_entry.is_verified = False
            otp_entry.attempt_count = 0
            db.commit()
            raise HTTPException(status_code=410, detail="OTP has expired.")

        if otp_entry.otp_code != otp_code:
            otp_entry.attempt_count = (otp_entry.attempt_count or 0) + 1
            if otp_entry.attempt_count >= max_attempts:
                otp_entry.status = "frozen"
            db.commit()
            raise HTTPException(status_code=422, detail="Invalid OTP.")

        otp_entry.is_verified = True
        otp_entry.status = "used"
        otp_entry.attempt_count = 0
        user_db.is_verified = True
        user_db.status = "active"

        db.commit()

        token, exp = signJWT(user_db.user_id, user_db.user_type)

        return {
            "msg": "OTP verified successfully, login successful",
            "user_id": user_db.user_id,
            "username": user_db.username,
            "phone_number": user_db.phone_number,
            "user_type": user_db.user_type,
            "is_verified": user_db.is_verified,
            "token": token,
            "created_at": user_db.created_at,
            "expires_at": exp
            
            
        }

    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Database error occurred during OTP verification: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"An unexpected error occurred during OTP verification: {e}")

@router.post("/v1/auth/login")
async def login(phone_number: str, db: Session = Depends(get_db)):
    try:
        cleanup_expired_otps(db)
        
        if not validate_phone_number(phone_number)["valid"]:
            raise HTTPException(status_code=422, detail="Invalid phone number.")
        
        user_db = db.query(User).filter(User.phone_number == phone_number).first()
        if not user_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User does not exist. Please register.")
        
        if not user_db.is_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Account not verified. Please complete registration verification first.")

        otp = generate_otp()
        now = datetime.now(timezone.utc)  
        expiry = now + timedelta(minutes=5)

        otp_entry = OTP(
            phone_number=phone_number, 
            purpose="login",
            otp_code=otp,
            attempt_count=0,
            is_verified=False,
            generated_at=now,
            expired_at=expiry,
            status="active"
        )

        db.add(otp_entry)
        db.commit()

        if not send_otp_sms(phone_number, otp):  
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to send OTP via SMS. Please try again later."
            )

        return {"message": "OTP sent to your phone number"}

    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Database error occurred during login. {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"An unexpected error occurred during login. Please try again. {str(e)}")

@router.post("/v1/auth/verify-login-otp", status_code=status.HTTP_200_OK)
def verify_otp(phone_number: str, otp_code: str, db: Session = Depends(get_db)):
    try:
        if not validate_phone_number(phone_number)["valid"]:
            raise HTTPException(status_code=422, detail="Invalid phone number.")

        user_db = db.query(User).filter(User.phone_number == phone_number).first()
        if not user_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        if not user_db.is_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Account not verified. Please complete registration verification first.")

        otp_entry = db.query(OTP).filter(
            OTP.phone_number == phone_number,
            OTP.purpose == "login",
            OTP.is_verified == False,
            OTP.status == "active"
        ).order_by(desc(OTP.generated_at)).first()

        if not otp_entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active OTP found for this user.")

        otp_expired_at = otp_entry.expired_at
        if otp_expired_at.tzinfo is None:
            otp_expired_at = otp_expired_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > otp_expired_at:
            otp_entry.status = "expired"
            otp_entry.is_verified = False
            db.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="OTP has expired.")

        if otp_entry.otp_code != otp_code:
            otp_entry.attempt_count = (otp_entry.attempt_count or 0) + 1
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP.")

        otp_entry.is_verified = True
        otp_entry.status = "used"
        db.commit()

        token, exp = signJWT(user_db.user_id, user_db.user_type)

        return {
            "msg": "OTP verified successfully, login successful",
            "user_id": user_db.user_id,
            "username": user_db.username,
            "phone_number": user_db.phone_number,
            "user_type": user_db.user_type,
            "is_verified": user_db.is_verified,
            "token": token,
            "created_at": user_db.created_at,
            "expires_at": exp
            
            
        }

    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Database error occurred during OTP verification. {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during OTP verification. Please try again. {str(e)}"
        )
    
@router.put("/v1/users/{user_id}")
def update_user(user_id: int, update_data: UserUpdateRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"User with ID {user_id} not found.")

        if update_data.username is not None:
            user.username = update_data.username
        if update_data.email is not None:
            user.email = update_data.email
        # if update_data.phone_number is not None:
        #     user.phone_number = update_data.phone_number
        
        user.updated_at=datetime.now(timezone.utc)

        db.commit()
        db.refresh(user)

        return {
            "message": f"User with ID {user_id} updated successfully.",
            "status": "success",
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                #"phone_number": user.phone_number,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Database error occurred while updating user. {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"An unexpected error occurred while updating user. Please try again. {e}")
    

@router.delete("/v1/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"User with ID {user_id} not found.")

        db.delete(user)
        db.commit()

        return {
            "message": f"User with ID {user_id} has been deleted successfully.",
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Database error occurred while deleting user. {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"An unexpected error occurred while deleting user. Please try again. {e}")
    
@router.get("/v1/all-users")
def get_all_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).filter(User.is_verified==True).all()

        formatted_users = [
            {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "phone_number": user.phone_number,
                "status": user.status,
                "user_type": user.user_type,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            for user in users
        ]

        return {
            "total_count": len(formatted_users),
            "users": formatted_users
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Database error occurred while fetching users. {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"An unexpected error occurred while fetching users. Please try again. {e}")






