import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketState
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
import secrets
from sqlalchemy.exc import SQLAlchemyError
from fastapi import status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from db.session import Base, SessionLocal, engine,get_db
from api.v1.endpoints.user import user_router
from api.v1.endpoints.onboarding import onboardings_router
from api.v1.endpoints.dish_recommendation import user_interactions_router
from api.v1.models import all_models
Base.metadata.create_all(bind=engine)


app = FastAPI(
    docs_url=None,
    redoc_url=None
)

security = HTTPBasic()
REALM = "swagger"

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = FastAPI.openapi(app)  
    openapi_schema["info"]["title"] = "VEREATY Backend"
    openapi_schema["info"]["version"] = "1.1.0"
    openapi_schema["info"]["description"] = "This API serves as the backend for VEREATY."
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(onboardings_router, prefix="/api", tags=["Onboarding"])
app.include_router(user_router, prefix="/api", tags=["User Auth"])
app.include_router(user_interactions_router, prefix="/api", tags=["Dish genrate"])


#------------------------------------- Swagger Security Docs ---------------------------------------------------

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "vinay")
    correct_password = secrets.compare_digest(credentials.password, "12345678")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": f'Basic realm="{REALM}"'},
        )

@app.get("/docs", include_in_schema=False)
def custom_docs(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Swagger UI")

@app.get("/redoc", include_in_schema=False)
def custom_redoc(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    return get_redoc_html(openapi_url="/openapi.json", title="Redoc")

#--------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8000, reload= True, host="0.0.0.0")