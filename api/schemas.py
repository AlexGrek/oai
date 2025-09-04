from typing import Any, Dict
from pydantic import BaseModel


class PostPipelineStr(BaseModel):
    pipeline: str
    input_str: str

class LoginCredentials(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

class StatusResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    data: Any

class CancelResponse(BaseModel):
    message: str
    cancelled: bool
    timestamp: str