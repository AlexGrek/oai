import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from api.v1 import app
import auth


# We'll use this library to handle colored output.
from colorama import Fore, Style, init

# Load environment variables from .env file


# Set up colorama
init(autoreset=True)


# Define a custom formatter with color
class ColoredFormatter(logging.Formatter):
    """
    A custom log formatter that adds color to log levels.
    """

    COLORS = {
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
        "DEBUG": Fore.CYAN,
    }

    # Define a new format string to include the color codes
    FORMAT = "%(levelname)s:\t\t%(message)s"

    def format(self, record):
        """
        Formats the log record.
        """
        # Get the color for the log level, or default to a reset style
        color = self.COLORS.get(record.levelname, Style.RESET_ALL)

        # Create a new formatter for this log record
        formatter = logging.Formatter(f"{color}{self.FORMAT}{Style.RESET_ALL}")

        # Use the new formatter to format the log record
        return formatter.format(record)


# Get the desired log level from environment variables, defaulting to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Set up logging for our entire application.
# We will not touch Uvicorn's loggers.
# By getting the root logger (with no name), we configure all loggers.
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Create a console handler for our application's logs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(LOG_LEVEL)

# Create and set our custom colored formatter
formatter = ColoredFormatter()
console_handler.setFormatter(formatter)

# Add the handler to the root logger
logger.addHandler(console_handler)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    logger.info("Root endpoint requested")
    return {
        "message": "OAI API Server",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "post": "/api/v1/post",
            "login": "/api/v1/login",
            "try_consume": "/api/v1/try_consume",
            "status": "/api/v1/status",
            "cancel": "/api/v1/cancel",
        },
    }


# Health check
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check requested")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn

    # This message will now be colored green, and Uvicorn's logs will be normal.
    logger.info(f"Auth tokens from env: {auth.active_tokens}")
    # We remove the log_config parameter to let Uvicorn use its default loggers
    uvicorn.run(app, host="0.0.0.0", port=8000)
