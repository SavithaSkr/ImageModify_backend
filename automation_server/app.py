import os
import sys
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Add modules folder to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "modules"))

from modules.processor import process_sheet

# Load environment variables
load_dotenv()

# Google service account creds from .env
GCP_INFO = {
    "type": os.getenv("GCP_TYPE"),
    "project_id": os.getenv("GCP_PROJECT_ID"),
    "private_key_id": os.getenv("GCP_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GCP_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("GCP_CLIENT_EMAIL"),
    "client_id": os.getenv("GCP_CLIENT_ID"),
    "auth_uri": os.getenv("GCP_AUTH_URI"),
    "token_uri": os.getenv("GCP_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GCP_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("GCP_CLIENT_CERT_URL"),
}

BASE_URL = os.getenv("BASE_URL")
STATIC_SHEET_ID = os.getenv("SHEET_ID")    # static mode
STATIC_SHEET_NAME = os.getenv("SHEET_NAME")
APP_API_KEY = os.getenv("APP_API_KEY")

# Build Google API Credentials
def build_credentials():
    return Credentials.from_service_account_info(
        GCP_INFO,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

# FastAPI App
app = FastAPI(title="Secure Image Automation API (Local Image Storage)")

# Serve static images
app.mount("/images", StaticFiles(directory="images"), name="images")

@app.get("/openapi.json")
def openapi_override():
    return app.openapi()


# API Key Verification
def verify_api_key(x_api_key: str = Header(None), request: Request = None):
    allowed = ["/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"]

    if request.url.path in allowed:
        return

    if x_api_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# -------------------------------
#  LOAD SHEET (supports both modes)
# -------------------------------
def load_sheet(sheet_id=None, sheet_name=None):
    creds = build_credentials()
    client = gspread.authorize(creds)

    # Static mode
    if not sheet_id:
        sheet_id = STATIC_SHEET_ID
        sheet_name = STATIC_SHEET_NAME

    ss = client.open_by_key(sheet_id)

    if sheet_name:
        return ss.worksheet(sheet_name)

    return ss.sheet1


# -------------------------------------------------
# STATIC MODE (existing behavior — untouched)
# -------------------------------------------------
@app.post("/run")
def run(background_tasks: BackgroundTasks, x_api_key: str = Header(None), request: Request = None):
    verify_api_key(x_api_key, request)

    sheet = load_sheet()  # static sheet
    background_tasks.add_task(process_sheet, sheet, BASE_URL)

    return {"status": "processing_started", "mode": "static"}


# -------------------------------------------------
# DYNAMIC MODE (NEW — requested by you)
# -------------------------------------------------
class DynamicRunPayload(BaseModel):
    sheet_id: str
    sheet_name: str | None = None


@app.post("/run-dynamic")
def run_dynamic(
    payload: DynamicRunPayload,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(None),
    request: Request = None
):
    verify_api_key(x_api_key, request)

    # Load dynamic sheet
    sheet = load_sheet(payload.sheet_id, payload.sheet_name)

    # Process in background
    background_tasks.add_task(process_sheet, sheet, BASE_URL)

    return {
        "status": "processing_started",
        "mode": "dynamic",
        "sheet_id": payload.sheet_id,
        "sheet_name": payload.sheet_name,
    }


# Health Check
@app.get("/health")
def health(x_api_key: str = Header(None), request: Request = None):
    verify_api_key(x_api_key, request)
    return {"status": "ok"}
