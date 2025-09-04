# Token storage with environment variable support
from typing import Optional, Set
import uuid
import os
from fastapi import Request

# Load tokens from environment variable
def load_tokens_from_env() -> Set[str]:
    """Load tokens from OAI_TOKENS environment variable"""
    tokens_str = os.getenv("OAI_TOKENS", "")
    if not tokens_str:
        return set()
    
    # Split by colon and strip whitespace from each token
    tokens = {token.strip() for token in tokens_str.split(":") if token.strip()}
    return tokens

# Initialize active tokens from environment
active_tokens: Set[str] = load_tokens_from_env()

def generate_dummy_token() -> str:
    """Generate a dummy JWT-like token"""
    return f"oai_token_{uuid.uuid4().hex[:16]}"

def add_token_to_active(token: str) -> None:
    """Add a token to active tokens set"""
    active_tokens.add(token)

def remove_token_from_active(token: str) -> None:
    """Remove a token from active tokens set"""
    active_tokens.discard(token)

def verify_token(request: Request) -> Optional[str]:
    """Verify token from cookies or Authorization header"""
    token = None
    
    # Check cookies first
    token = request.cookies.get("access_token")
    
    if not token:
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    return token if token and token in active_tokens else None

def refresh_tokens_from_env() -> None:
    """Refresh active tokens from environment variable (useful for runtime updates)"""
    global active_tokens
    active_tokens = load_tokens_from_env()
