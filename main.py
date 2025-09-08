"""
Main application entry point for the Risk Processing API.

This module serves as the entry point for the FastAPI application,
configuring the server and making it ready for deployment.
"""

import uvicorn
from src.api.routes import app
from src.services.logger_service import LoggerService
from src.config.constants import API_TITLE, API_VERSION

# Initialize logger
logger = LoggerService()

# Log application startup
logger.log_info(f"{API_TITLE} v{API_VERSION} initializing")

if __name__ == "__main__":
    """
    Run the application with uvicorn server.
    
    This block is executed when the script is run directly,
    typically for development purposes.
    """
    logger.log_info("Starting development server")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        reload=False  # Set to True for development with auto-reload
    )