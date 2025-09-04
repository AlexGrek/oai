import logging
import os
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field
from fastapi import HTTPException

from engine.waiter import ApiWaiter

# Configure logging for the module
logger = logging.getLogger(__name__)

# Global variable to hold a singleton instance of the client
_client_instance = None

def qpart(value: str) -> str:
    """Quote a URL path segment (slashes are unsafe)."""
    return urllib.parse.quote(value or "", safe="")


class Message(BaseModel):
    """Message model for chat interactions."""

    role: str = Field(
        ..., description="Role of the message sender (system, user, assistant)"
    )
    content: str = Field(..., description="Content of the message")


class TaskPayload(BaseModel):
    """Payload for task submission."""

    model: str = Field(..., description="Model name")
    o_format: Optional[str] = Field(
        default=None, description="Enable or disable JSON mode", alias="format"
    )
    stream: bool = Field(default=False, description="Whether to stream the response")
    messages: List[Message] = Field(
        ..., description="List of messages for the conversation"
    )


class TaskRequest(BaseModel):
    """Complete task request model."""

    capability: str = Field(..., description="Capability string in format LLM::{model}")
    urgent: bool = Field(default=False, description="Whether the task is urgent")
    payload: TaskPayload = Field(..., description="Task payload")
    apiKey: str = Field(..., alias="apiKey", description="API key for authentication")


class CapabilitiesRequest(BaseModel):
    """Request model for capabilities endpoint."""

    apiKey: str = Field(..., alias="apiKey", description="API key for authentication")


class PollRequest(BaseModel):
    """Request model for polling task status."""

    apiKey: str = Field(..., alias="apiKey", description="API key for authentication")


class TaskResponse(BaseModel):
    """Response model for task submission."""

    id: Optional[str] = None
    capability: Optional[str] = None
    status: Optional[str] = None
    result: Optional[Any] = None


class BackendAPIClient:
    """
    Asynchronous client for interacting with the backend API using httpx.
    """

    def __init__(self, token: str, backend_url: str):
        """
        Initialize the API client.

        Args:
            token: API token for authentication.
            backend_url: Base URL of the backend API.
        """
        self.token = token
        self.backend_url = backend_url.rstrip("/")
        # Use httpx.AsyncClient for asynchronous requests
        self.session = httpx.AsyncClient()

    def set_token(self, token: str):
        """Update the API token."""
        self.token = token

    def set_backend_url(self, backend_url: str):
        """Update the backend URL."""
        self.backend_url = backend_url.rstrip("/")

    async def check_capabilities_online(self) -> Dict[str, Any]:
        """
        Check online capabilities asynchronously.

        Returns:
            Response from the capabilities endpoint.
        """
        url = f"{self.backend_url}/api/capabilities/online"
        request_data = CapabilitiesRequest(apiKey=self.token)

        response = await self.session.post(
            url,
            json=request_data.model_dump(by_alias=True),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    async def submit_task_blocking(
        self,
        model: str,
        system_message: str,
        user_message: str,
        json_mode: bool,
    ) -> Dict[str, Any]:
        """
        Submit a task and wait for completion (blocking) asynchronously.

        Args:
            model: The model to use.
            system_message: System message content.
            user_message: User message content.

        Returns:
            Response from the task submission.
        """
        url = f"{self.backend_url}/api/task/submit_blocking"
        messages = [
            Message(role="system", content=system_message),
            Message(role="user", content=user_message),
        ]
        payload = TaskPayload(
            model=model,
            stream=False,
            messages=messages,
            format="json" if json_mode else None,
        )
        request_data = TaskRequest(
            capability=f"{model}", urgent=False, payload=payload, apiKey=self.token
        )

        response = await self.session.post(
            url,
            json=request_data.model_dump(by_alias=True),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    async def submit_task(
        self, model: str, system_message: str, user_message: str, json_mode: bool
    ) -> Dict[str, Any]:
        """
        Submit a task (non-blocking) asynchronously.

        Args:
            model: The model to use.
            system_message: System message content.
            user_message: User message content.

        Returns:
            Response from the task submission.
        """
        url = f"{self.backend_url}/api/task/submit"
        messages = [
            Message(role="system", content=system_message),
            Message(role="user", content=user_message),
        ]
        payload = TaskPayload(
            model=model,
            stream=False,
            messages=messages,
            format="json" if json_mode else None,
        )
        request_data = TaskRequest(
            capability=f"{model}",
            urgent=False,
            payload=payload,
            apiKey=self.token,
        )

        logger.info(request_data.model_dump_json())

        response = await self.session.post(
            url,
            json=request_data.model_dump(by_alias=True),
            headers={"Content-Type": "application/json"},
            timeout=None,
        )
        if response.is_error:
            logger.error(response.content)
        response.raise_for_status()
        return response.json()

    def create_task_waiter(self, capability: str, task_id: str) -> ApiWaiter:
        encoded_capability = qpart(capability)
        url = f"{self.backend_url}/api/task/poll/{encoded_capability}/{task_id}"
        request_data = PollRequest(apiKey=self.token)
        return ApiWaiter(url, request_data)

    async def poll_task(self, capability: str, task_id: str) -> Dict[str, Any]:
        """
        Poll for task status/results asynchronously.

        Args:
            capability: The capability string (e.g., "LLM::gpt-4").
            task_id: The task ID to poll.

        Returns:
            Response from the polling endpoint.
        """
        encoded_capability = qpart(capability)
        url = f"{self.backend_url}/api/task/poll/{encoded_capability}/{task_id}"
        request_data = PollRequest(apiKey=self.token)

        response = await self.session.post(
            url,
            json=request_data.model_dump(by_alias=True),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def get_async_api_client() -> BackendAPIClient:
    """
    This dependency function provides a singleton instance of BackendAPIClient.
    The instance is created only on the first request it's needed.
    """
    global _client_instance

    if _client_instance is None:
        logger.info("First call to get_async_api_client. Initializing the client.")
        token = os.getenv("OFFLOADMQ_TOKEN")
        backend_url = os.getenv("OFFLOADMQ_BACKEND_URL")

        if not token or not backend_url:
            raise HTTPException(
                status_code=500,
                detail="Missing required environment variables (OFFLOADMQ_TOKEN, OFFLOADMQ_BACKEND_URL)",
            )

        _client_instance = BackendAPIClient(token=token, backend_url=backend_url)

    return _client_instance
