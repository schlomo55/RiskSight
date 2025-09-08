"""
Pydantic data models for the Risk Processing Engine.

Defines input validation models and response structures for the API endpoints.
All models include comprehensive validation and documentation.
"""

from typing import Optional, Union
from pydantic import BaseModel, Field, validator
from src.config.constants import (
    WEATHER_CATEGORIES, CRIME_RANGE, ACCIDENT_RANGE, SOCIO_RANGE
)


class RiskDataInput(BaseModel):
    """
    Input model for risk data validation.
    
    Validates all risk indicators according to the specified ranges
    and ensures weather categories are from the allowed list.
    """
    city: Optional[str] = Field(
        default=None,
        description="City name (optional)",
        min_length=1,
        max_length=100
    )
    
    crime_index: Union[int, float] = Field(
        ...,
        description=f"Crime index ({CRIME_RANGE[0]}-{CRIME_RANGE[1]} scale)",
        ge=CRIME_RANGE[0],
        le=CRIME_RANGE[1]
    )
    
    accident_rate: Union[int, float] = Field(
        ...,
        description=f"Accident rate ({ACCIDENT_RANGE[0]}-{ACCIDENT_RANGE[1]} scale)",
        ge=ACCIDENT_RANGE[0],
        le=ACCIDENT_RANGE[1]
    )
    
    socioeconomic_level: Union[int, float] = Field(
        ...,
        description=f"Socioeconomic level ({SOCIO_RANGE[0]}-{SOCIO_RANGE[1]} scale)",
        ge=SOCIO_RANGE[0],
        le=SOCIO_RANGE[1]
    )
    
    weather: str = Field(
        ...,
        description=f"Weather conditions. Allowed values: {list(WEATHER_CATEGORIES.keys())}"
    )
    
    @validator('weather')
    def validate_weather_category(cls, v:str):
        """Validate weather category against allowed values (case-insensitive)."""
        # Create case-insensitive mapping for weather categories
        weather_mapping = {key.lower(): key for key in WEATHER_CATEGORIES.keys()}
        
        # Convert input to lowercase for comparison
        v_lower = v.lower()
        
        if v_lower not in weather_mapping:
            raise ValueError(f"Unknown weather: {v}")
            
        # Return the properly formatted weather value
        return weather_mapping[v_lower]
    
    @validator('city')
    def validate_city_name(cls, v):
        """Validate and clean city name."""
        if v is not None:
            # Remove extra whitespace and ensure non-empty
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("City name cannot be empty or whitespace only")
            return cleaned
        return v
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "city": "New York",
                "crime_index": 7.5,
                "accident_rate": 6.2,
                "socioeconomic_level": 4,
                "weather": "Rainy"
            }
        }


class RiskComponents(BaseModel):
    """
    Model for individual risk component scores.
    
    Contains the breakdown of risk scores by component
    for transparency and analysis.
    """
    crime_component: float = Field(
        ...,
        description="Crime risk component score (0-100)",
        ge=0,
        le=100
    )
    
    accident_component: float = Field(
        ...,
        description="Accident risk component score (0-100)",
        ge=0,
        le=100
    )
    
    socioeconomic_component: float = Field(
        ...,
        description="Socioeconomic risk component score (0-100)",
        ge=0,
        le=100
    )
    
    weather_component: float = Field(
        ...,
        description="Weather risk component score (0-100)",
        ge=0,
        le=100
    )


class RiskProcessingResult(BaseModel):
    """
    Complete risk processing result model.
    
    Contains the final risk score and component breakdown
    for a single risk assessment.
    """
    city: Optional[str] = Field(
        default=None,
        description="City name if provided"
    )
    
    risk_score: float = Field(
        ...,
        description="Final aggregated risk score (0-100)",
        ge=0,
        le=100
    )
    
    components: RiskComponents = Field(
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


class ProcessingError(BaseModel):
    """
    Error model for processing failures.
    
    Used in CSV processing to track row-level errors
    while maintaining consistent response structure.
    """
    row_number: Optional[int] = Field(
        default=None,
        description="Row number where error occurred (for CSV processing)"
    )
    
    error_message: str = Field(
        ...,
        description="Detailed error message"
    )
    
    error_type: str = Field(
        default="validation_error",
        description="Type of error (validation_error, processing_error, etc.)"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "row_number": 25,
                "error_message": "Unknown weather: Foggy",
                "error_type": "validation_error"
            }
        }


class CSVProcessingSummary(BaseModel):
    """
    Summary model for CSV processing results.
    
    Provides statistics about the batch processing operation
    including success and error counts.
    """
    total_rows: int = Field(
        ...,
        description="Total number of rows processed",
        ge=0
    )
    
    successful_rows: int = Field(
        ...,
        description="Number of successfully processed rows",
        ge=0
    )
    
    error_rows: int = Field(
        ...,
        description="Number of rows with errors",
        ge=0
    )
    
    processing_time_seconds: float = Field(
        ...,
        description="Total processing time in seconds",
        ge=0
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "total_rows": 1000,
                "successful_rows": 985,
                "error_rows": 15,
                "processing_time_seconds": 12.45
            }
        }