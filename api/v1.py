from fastapi import FastAPI, Form, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from api.schemas import *
from auth import *
from engine.apiclient import BackendAPIClient, get_async_api_client
from engine.taskmaster import Taskmaster, get_async_taskmaster

# Initialize FastAPI app
app = FastAPI(title="OAI API", version="1.0.0")

from fastapi import FastAPI, HTTPException, Response, Request, Depends, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import httpx
import uuid
from datetime import datetime, timedelta

# Initialize FastAPI app
app = FastAPI(title="OAI API", version="1.0.0")


def get_token_from_request(request: Request) -> Optional[str]:
    """Extract token from Authorization header or cookies"""
    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        if token in active_tokens:
            return token

    # Check cookies
    token = request.cookies.get("access_token")
    if token and token in active_tokens:
        return token

    return None


def require_auth(request: Request) -> str:
    """Dependency to require valid authentication"""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide token via Authorization header or cookies.",
        )
    return token


# Create router for /api/v1 with authentication dependency
api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])

# Create router for public endpoints (no auth required)
public_router = APIRouter(prefix="/api/v1")


# Protected endpoints (require authentication)
@api_router.post("/post")
async def post_data(
    data: PostPipelineStr, taskmaster: Taskmaster = Depends(get_async_taskmaster)
):
    response = await taskmaster.new_request(data.pipeline, data.input_str)
    return {"result": response}


@api_router.get("/try_consume")
async def try_consume():
    """Return 202 with retry-after header (requires authentication)"""
    headers = {"Retry-After": "30"}  # Retry after 30 seconds
    return JSONResponse(
        status_code=202,
        content={
            "message": "Request accepted but not yet processed",
            "status": "processing",
            "retry_after_seconds": 30,
        },
        headers=headers,
    )


@api_router.get("/status", response_model=StatusResponse)
async def get_status(client: BackendAPIClient = Depends(get_async_api_client)):
    """Return API status information (requires authentication)"""
    data = await client.check_capabilities_online()
    return StatusResponse(
        status="operational",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        data=data,
    )


@api_router.post("/cancel", response_model=CancelResponse)
async def cancel_operation():
    """Cancel an operation (requires authentication)"""
    return CancelResponse(
        message="Operation cancelled successfully",
        cancelled=True,
        timestamp=datetime.utcnow().isoformat(),
    )


@api_router.post("/send_request")
async def send_request(url: str, method: str = "GET"):
    """
    Example endpoint that demonstrates sending HTTP requests using httpx
    This shows how the app can SEND requests, not just RECEIVE them
    (requires authentication)
    """
    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, timeout=10.0)
            elif method.upper() == "POST":
                response = await client.post(url, json={}, timeout=10.0)
            else:
                raise HTTPException(
                    status_code=400, detail="Only GET and POST methods supported"
                )

            return {
                "url": url,
                "method": method.upper(),
                "status_code": response.status_code,
                "response_preview": (
                    response.text[:200] + "..."
                    if len(response.text) > 200
                    else response.text
                ),
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@public_router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    credentials: Optional[LoginCredentials] = None,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
):
    """Accept credentials via JSON or form data and return token with cookies (no auth required)"""
    # Extract credentials from JSON body or form data
    if credentials:
        # JSON request
        user = credentials.username
        pwd = credentials.password
    elif username and password:
        # Form data request
        user = username
        pwd = password
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide credentials either as JSON body {'username': '...', 'password': '...'} or as form data",
        )

    # Dummy authentication (accept any non-empty credentials)
    if not user or not pwd:
        raise HTTPException(status_code=400, detail="Username and password required")

    # For demo purposes, reject if username is "invalid"
    if user == "invalid":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate dummy token
    token = generate_dummy_token()
    active_tokens.add(token)

    # Set cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,  # 1 hour
        samesite="lax",
    )

    return TokenResponse(access_token=token, token_type="bearer", expires_in=3600)


# Include routers
app.include_router(api_router)
app.include_router(public_router)
