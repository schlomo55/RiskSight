"""
Dual logging service for the Risk Processing Engine.

Provides comprehensive logging functionality with separate files for
general information and errors, ISO-8601 timestamps, and structured
formatting according to the system requirements.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Any
from src.config.constants import (
    GENERAL_LOG_PATH, ERROR_LOG_PATH, LOG_FORMAT, LOG_DATE_FORMAT
)


class LoggerService:
    """
    Dual logging service that maintains separate log files for general
    information and errors, with proper formatting and timestamp handling.
    
    Features:
    - Separate general.log and error.log files
    - ISO-8601 timestamp format
    - Structured, human-readable format
    - Automatic log directory creation
    - Context-aware logging methods
    - No sensitive data exposure
    """
    
    _instance: Optional['LoggerService'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'LoggerService':
        """Singleton pattern to ensure consistent logging across the application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the dual logging system."""
        if self._initialized:
            return
        
        self._setup_logging_infrastructure()
        self._create_loggers()
        self._initialized = True
    
    def _setup_logging_infrastructure(self):
        """Set up logging directories and basic configuration."""
        # Ensure log directories exist
        general_log_dir = Path(GENERAL_LOG_PATH).parent
        error_log_dir = Path(ERROR_LOG_PATH).parent
        
        general_log_dir.mkdir(parents=True, exist_ok=True)
        error_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure basic logging settings
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT
        )
    
    def _create_loggers(self):
        """Create and configure the general and error loggers."""
        # Create custom formatter with ISO-8601 timestamps
        formatter = logging.Formatter(
            fmt=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT
        )
        
        # General logger for informational messages
        self.general_logger = logging.getLogger('risk_processor.general')
        self.general_logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.general_logger.handlers.clear()
        
        # File handler for general log
        general_handler = logging.FileHandler(
            GENERAL_LOG_PATH, 
            mode='a', 
            encoding='utf-8'
        )
        general_handler.setLevel(logging.INFO)
        general_handler.setFormatter(formatter)
        self.general_logger.addHandler(general_handler)
        
        # Error logger for error messages
        self.error_logger = logging.getLogger('risk_processor.error')
        self.error_logger.setLevel(logging.ERROR)
        
        # Remove existing handlers to avoid duplicates
        self.error_logger.handlers.clear()
        
        # File handler for error log
        error_handler = logging.FileHandler(
            ERROR_LOG_PATH, 
            mode='a', 
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.error_logger.addHandler(error_handler)
        
        # Prevent propagation to root logger to avoid duplicate messages
        self.general_logger.propagate = False
        self.error_logger.propagate = False
    
    def log_info(self, message: str, context: Optional[dict] = None):
        """
        Log informational message to general.log.
        
        Args:
            message: The message to log
            context: Optional context dictionary (will be sanitized)
        """
        formatted_message = self._format_message(message, context)
        self.general_logger.info(formatted_message)
    
    def log_debug(self, message: str, context: Optional[dict] = None):
        """
        Log debug message to general.log.
        
        Args:
            message: The message to log
            context: Optional context dictionary (will be sanitized)
        """
        formatted_message = self._format_message(message, context)
        self.general_logger.debug(formatted_message)
    
    def log_warning(self, message: str, context: Optional[dict] = None):
        """
        Log warning message to general.log.
        
        Args:
            message: The message to log
            context: Optional context dictionary (will be sanitized)
        """
        formatted_message = self._format_message(message, context)
        self.general_logger.warning(formatted_message)
    
    def log_error(self, message: str, error: Optional[Exception] = None, context: Optional[dict] = None):
        """
        Log error message to error.log.
        
        Args:
            message: The error message to log
            error: Optional exception object for stack trace
            context: Optional context dictionary (will be sanitized)
        """
        formatted_message = self._format_message(message, context)
        
        if error:
            # Include exception information
            formatted_message += f" | Exception: {str(error)} | Type: {type(error).__name__}"
            
            # Log with exception info for stack trace
            self.error_logger.error(formatted_message, exc_info=error)
        else:
            self.error_logger.error(formatted_message)
    
    def log_critical(self, message: str, error: Optional[Exception] = None, context: Optional[dict] = None):
        """
        Log critical error message to error.log.
        
        Args:
            message: The critical error message to log
            error: Optional exception object for stack trace
            context: Optional context dictionary (will be sanitized)
        """
        formatted_message = self._format_message(message, context)
        
        if error:
            formatted_message += f" | Exception: {str(error)} | Type: {type(error).__name__}"
            self.error_logger.critical(formatted_message, exc_info=error)
        else:
            self.error_logger.critical(formatted_message)
    
    def log_processing_start(self, operation: str, details: Optional[dict] = None):
        """
        Log the start of a processing operation.
        
        Args:
            operation: Name of the operation starting
            details: Optional operation details (will be sanitized)
        """
        message = f"Starting {operation}"
        self.log_info(message, details)
    
    def log_processing_complete(self, operation: str, details: Optional[dict] = None):
        """
        Log the completion of a processing operation.
        
        Args:
            operation: Name of the operation completed
            details: Optional operation results (will be sanitized)
        """
        message = f"Completed {operation}"
        self.log_info(message, details)
    
    def log_validation_error(self, field: str, value: Any, error_message: str, row_number: Optional[int] = None):
        """
        Log validation error with structured format.
        
        Args:
            field: Field name that failed validation
            value: The invalid value (will be sanitized)
            error_message: Validation error message
            row_number: Optional row number for CSV processing
        """
        context = {
            "field": field,
            "error": error_message
        }
        
        if row_number is not None:
            context["row"] = row_number
        
        # Sanitize the value to avoid logging sensitive data
        sanitized_value = self._sanitize_value(value)
        context["value"] = sanitized_value
        
        message = f"Validation failed for field '{field}'"
        self.log_error(message, context=context)
    
    def log_csv_processing_summary(self, total_rows: int, success_count: int, error_count: int, processing_time: float):
        """
        Log CSV processing summary statistics.
        
        Args:
            total_rows: Total number of rows processed
            success_count: Number of successfully processed rows
            error_count: Number of rows with errors
            processing_time: Processing time in seconds
        """
        summary = {
            "total_rows": total_rows,
            "successful_rows": success_count,
            "error_rows": error_count,
            "processing_time_seconds": round(processing_time, 2)
        }
        
        message = f"{error_count} errors out of {total_rows} rows processed"
        self.log_info(f"CSV processing summary: {message}", summary)
    
    def _format_message(self, message: str, context: Optional[dict] = None) -> str:
        """
        Format message with optional context information.
        
        Args:
            message: Base message
            context: Optional context dictionary
            
        Returns:
            Formatted message string
        """
        if not context:
            return message
        
        # Sanitize context to remove sensitive data
        sanitized_context = self._sanitize_context(context)
        
        # Format context as key-value pairs
        context_str = " | ".join([f"{k}: {v}" for k, v in sanitized_context.items()])
        
        return f"{message} | {context_str}"
    
    def _sanitize_context(self, context: dict) -> dict:
        """
        Sanitize context dictionary to remove sensitive information.
        
        Args:
            context: Original context dictionary
            
        Returns:
            Sanitized context dictionary
        """
        sanitized = {}
        sensitive_fields = {'password', 'token', 'key', 'secret', 'auth'}
        
        for key, value in context.items():
            if any(sensitive_field in key.lower() for sensitive_field in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = self._sanitize_value(value)
        
        return sanitized
    
    def _sanitize_value(self, value: Any) -> Any:
        """
        Sanitize individual values to prevent sensitive data exposure.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
        """
        if isinstance(value, str):
            # Limit string length to prevent log pollution
            if len(value) > 200:
                return value[:200] + "..."
            return value
        elif isinstance(value, (int, float)):
            return value
        elif isinstance(value, (list, tuple)):
            # Limit collection size
            if len(value) > 10:
                return f"[{len(value)} items]"
            return [self._sanitize_value(item) for item in value]
        elif isinstance(value, dict):
            # Recursively sanitize dictionaries
            if len(value) > 10:
                return f"{{dict with {len(value)} keys}}"
            return {k: self._sanitize_value(v) for k, v in value.items()}
        else:
            # Convert other types to string representation
            return str(value)
    
    def get_log_file_paths(self) -> dict:
        """
        Get the current log file paths.
        
        Returns:
            Dictionary with general and error log file paths
        """
        return {
            "general_log": GENERAL_LOG_PATH,
            "error_log": ERROR_LOG_PATH
        }
    
    def check_log_files_exist(self) -> dict:
        """
        Check if log files exist and are writable.
        
        Returns:
            Dictionary with file existence and writability status
        """
        general_exists = os.path.exists(GENERAL_LOG_PATH)
        error_exists = os.path.exists(ERROR_LOG_PATH)
        
        general_writable = general_exists and os.access(GENERAL_LOG_PATH, os.W_OK)
        error_writable = error_exists and os.access(ERROR_LOG_PATH, os.W_OK)
        
        return {
            "general_log": {"exists": general_exists, "writable": general_writable},
            "error_log": {"exists": error_exists, "writable": error_writable}
        }