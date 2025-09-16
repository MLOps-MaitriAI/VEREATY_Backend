import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()  

# -------------------- ENV --------------------
ENV = os.getenv("ENV", "development")

if ENV == "production":
    TWILIO_ACCOUNT_SID = os.getenv("PROD_TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("PROD_TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("PROD_TWILIO_PHONE_NUMBER")
else:
    TWILIO_ACCOUNT_SID = os.getenv("DEV_TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("DEV_TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("DEV_TWILIO_PHONE_NUMBER")


def send_otp_sms(phone_number: str, otp: str):
    try:
        print("phone_number",phone_number)
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            body=f"Your vereaty login OTP is {otp}. It is valid for 5 mins. Do not share this code with anyone."
        )
        return True
    except Exception as e:
        #print(f"SMS Error: {e}")
        return False





