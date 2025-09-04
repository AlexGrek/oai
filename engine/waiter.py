import asyncio
import json
from typing import Any, Optional

import httpx
from pydantic import BaseModel


class ApiWaiter:
    """
    A class to asynchronously poll an API endpoint.

    It sends a GET request every 5 seconds until the JSON response
    contains a "status" key with a value of "completed", "failed", or "canceled".
    """

    def __init__(self, url: str, payload: BaseModel):
        """Initializes the ApiWaiter instance."""
        # Use an async client from httpx for making requests.
        self.client = httpx.AsyncClient()
        self.payload = payload
        self.url = url

    async def wait_for_status(self, url: Optional[str] = None) -> dict:
        """
        Polls the specified URL until a terminal status is received.

        Args:
            url (str): The API endpoint URL to poll.

        Returns:
            dict: The final JSON response from the API.

        Raises:
            Exception: If an unexpected error occurs during the API call.
        """
        if url is None:
            url = self.url

        print(f"Starting to poll API at {url}")

        # An infinite loop to keep polling until a condition is met.
        while True:
            try:
                # Use the httpx AsyncClient to send a GET request.
                request_data = self.payload

                response = await self.client.post(
                    url,
                    json=request_data.model_dump(by_alias=True),
                    headers={"Content-Type": "application/json"},
                )

                # Raise an exception for bad status codes (4xx or 5xx).
                response.raise_for_status()

                # Parse the JSON response.
                data = response.json()

                # Check for the status key and its value.
                if "status" in data:
                    status = data["status"].lower()
                    print(f"Current status: {status}")
                    if status in ["completed", "failed", "canceled"]:
                        print(f"Terminal status '{status}' reached. Stopping.")
                        return data  # Return the final JSON data.
                else:
                    print("Response does not contain a 'status' key. Retrying.")

            except httpx.HTTPStatusError as e:
                # Handle HTTP status errors (e.g., 404 Not Found, 500 Internal Server Error).
                print(
                    f"API request failed with status code {e.response.status_code}: {e}"
                )
            except httpx.RequestError as e:
                # Handle general request errors (e.g., network issues, timeouts).
                print(f"An error occurred while requesting {e.request.url!r}: {e}")
            except json.JSONDecodeError as e:
                # Handle errors if the response is not valid JSON.
                print(f"Failed to decode JSON from response: {e}")
            except Exception as e:
                # Handle any other unexpected errors.
                print(f"An unexpected error occurred: {e}")

            # Wait for 5 seconds before the next request.
            await asyncio.sleep(5)

    async def __aexit__(self):
        """Clean up the httpx client."""
        await self.client.aclose()
