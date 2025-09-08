"""
Response models for the Risk Processing API.

Defines structured response formats for all API endpoints with proper
validation, documentation, and example schemas for OpenAPI generation.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class RiskComponentsResponse(BaseModel):
    """
    Response model for individual risk component scores.
    
    Contains the breakdown of risk scores by component
    for transparency and analysis.
    """
    crime_component: float = Field(
        ...,
        description="Crime risk component score (0-100)",
        ge=0,
        le=100,
        example=75.0
    )
    
    accident_component: float = Field(
        ...,
        description="Accident risk component score (0-100)",
        ge=0,
        le=100,
        example=62.0
    )
    
    socioeconomic_component: float = Field(
        ...,
        description="Socioeconomic risk component score (0-100)",
        ge=0,
        le=100,
        example=60.0
    )
    
    weather_component: float = Field(
        ...,
        description="Weather risk component score (0-100)",
        ge=0,
        le=100,
        example=50.0
    )


class RiskProcessingResponse(BaseModel):
    """
    Main response model for risk processing results.
    
    Contains the final aggregated risk score and detailed
    component breakdown for a single risk assessment.
    """
    city: Optional[str] = Field(
        default=None,
        description="City name if provided in the request",
        example="New York"
    )
    
    risk_score: float = Field(
        ...,
        description="Final aggregated risk score (0-100 scale)",
        ge=0,
        le=100,
        example=72.45
    )
    
    components: RiskComponentsResponse = Field(
        ...,
        description="Individual component scores breakdown"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "city": "New York",
                "risk_score": 72.45,
                "components": {
                    "crime_component": 75.0,
                    "accident_component": 62.0,
                    "socioeconomic_component": 60.0,
                    "weather_component": 50.0
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response model for API error cases.
    
    Provides consistent error reporting across all endpoints
    with detailed error information for debugging.
    """
    detail: str = Field(
        ...,
        description="Detailed error message",
        example="Unknown weather: Foggy"
    )
    
    error_type: Optional[str] = Field(
        default="validation_error",
        description="Type of error that occurred",
        example="validation_error"
    )
    
    field: Optional[str] = Field(
        default=None,
        description="Field name that caused the error (if applicable)",
        example="weather"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "detail": "Unknown weather: Foggy",
                "error_type": "validation_error",
                "field": "weather"
            }
        }


class CSVProcessingStatusResponse(BaseModel):
    """
    Response model for CSV processing status information.
    
    Provides summary statistics about CSV processing operations
    including success/error counts and processing time.
    """
    filename: str = Field(
        ...,
        description="Name of the processed CSV file",
        example="risk_data.csv"
    )
    
    total_rows: int = Field(
        ...,
        description="Total number of rows in the CSV file",
        ge=0,
        example=1000
    )
    
    successful_rows: int = Field(
        ...,
        description="Number of successfully processed rows",
        ge=0,
        example=985
    )
    
    error_rows: int = Field(
        ...,
        description="Number of rows with processing errors",
        ge=0,
        example=15
    )
    
    processing_time_seconds: float = Field(
        ...,
        description="Total processing time in seconds",
        ge=0,
        example=12.45
    )
    
    download_ready: bool = Field(
        default=True,
        description="Whether the processed CSV is ready for download",
        example=True
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "filename": "risk_data.csv",
                "total_rows": 1000,
                "successful_rows": 985,
                "error_rows": 15,
                "processing_time_seconds": 12.45,
                "download_ready": True
            }
        }


class HealthCheckResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Provides system status information for monitoring
    and health checking purposes.
    """
    status: str = Field(
        default="healthy",
        description="Overall system status",
        example="healthy"
    )
    
    timestamp: str = Field(
        ...,
        description="Current timestamp in ISO format",
        example="2023-09-08T14:46:00Z"
    )
    
    version: str = Field(
        default="1.0.0",
        description="API version",
        example="1.0.0"
    )
    
    components: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of individual system components",
        example={
            "risk_processor": "healthy",
            "csv_processor": "healthy",
            "logging": "healthy"
        }
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2023-09-08T14:46:00Z",
                "version": "1.0.0",
                "components": {
                    "risk_processor": "healthy",
                    "csv_processor": "healthy",
                    "logging": "healthy"
                }
            }
        }


class ProcessorInfoResponse(BaseModel):
    """
    Response model for processor configuration information.
    
    Provides details about the current risk processor
    configuration for debugging and system information.
    """
    weights: Dict[str, float] = Field(
        ...,
        description="Current component weights configuration",
        example={
            "crime_index": 0.30,
            "accident_rate": 0.25,
            "socioeconomic_level": 0.25,
            "weather": 0.20
        }
    )
    
    rules_count: int = Field(
        ...,
        description="Number of active amplification rules",
        ge=0,
        example=2
    )
    
    noise_level: float = Field(
        ...,
        description="Current statistical noise level",
        ge=0,
        le=1,
        example=0.05
    )
    
    weather_categories: list = Field(
        ...,
        description="Supported weather categories",
        example=["Clear", "Rainy", "Snowy", "Stormy", "Extreme"]
    )
    
    output_scale: int = Field(
        ...,
        description="Output scale for risk scores",
        example=100
    )
    
    csv_max_workers: int = Field(
        ...,
        description="Number of CSV processing workers",
        ge=1,
        example=8
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "weights": {
                    "crime_index": 0.30,
                    "accident_rate": 0.25,
                    "socioeconomic_level": 0.25,
                    "weather": 0.20
                },
                "rules_count": 2,
                "noise_level": 0.05,
                "weather_categories": ["Clear", "Rainy", "Snowy", "Stormy", "Extreme"],
                "output_scale": 100,
                "csv_max_workers": 8
            }
        }


class ValidationErrorDetails(BaseModel):
    """
    Detailed validation error information for complex validation failures.
    
    Provides structured information about validation errors
    with field-specific error messages.
    """
    field: str = Field(
        ...,
        description="Field name that failed validation",
        example="crime_index"
    )
    
    provided_value: Any = Field(
        ...,
        description="The value that was provided",
        example="invalid"
    )
    
    expected: str = Field(
        ...,
        description="Description of expected value format",
        example="Number between 0 and 10"
    )
    
    error_message: str = Field(
        ...,
        description="Specific error message for this field",
        example="crime_index must be a number, got str"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "field": "crime_index",
                "provided_value": "invalid",
                "expected": "Number between 0 and 10",
                "error_message": "crime_index must be a number, got str"
            }
        }


class DetailedErrorResponse(BaseModel):
    """
    Detailed error response with field-specific validation errors.
    
    Used for complex validation failures that affect multiple
    fields or require detailed error reporting.
    """
    message: str = Field(
        ...,
        description="Overall error message",
        example="Multiple validation errors occurred"
    )
    
    errors: list[ValidationErrorDetails] = Field(
        ...,
        description="List of specific field validation errors"
    )
    
    total_errors: int = Field(
        ...,
        description="Total number of validation errors",
        ge=1,
        example=2
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "message": "Multiple validation errors occurred",
                "errors": [
                    {
                        "field": "crime_index",
                        "provided_value": "invalid",
                        "expected": "Number between 0 and 10",
                        "error_message": "crime_index must be a number, got str"
                    },
                    {
                        "field": "weather",
                        "provided_value": "Foggy",
                        "expected": "One of: Clear, Rainy, Snowy, Stormy, Extreme",
                        "error_message": "Unknown weather: Foggy"
                    }
                ],
                "total_errors": 2
            }
        }