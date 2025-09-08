"""
Input validation module for the Risk Processing Engine.

Provides comprehensive validation logic for risk data inputs including
range checking, type validation, and strict weather category validation.
"""

from typing import Dict, Any, List
import pandas as pd
from src.config.constants import (
    WEATHER_CATEGORIES, CRIME_RANGE, ACCIDENT_RANGE, SOCIO_RANGE,
    REJECT_UNKNOWN_WEATHER, CSV_REQUIRED_COLUMNS
)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class RiskDataValidator:
    """
    Validates risk data inputs with comprehensive error checking.
    
    Performs strict validation according to the configuration constants
    and provides detailed error messages for debugging and user feedback.
    """
    
    def __init__(self):
        """Initialize the validator with current configuration."""
        self.weather_categories = WEATHER_CATEGORIES
        self.crime_range = CRIME_RANGE
        self.accident_range = ACCIDENT_RANGE
        self.socio_range = SOCIO_RANGE
        self.reject_unknown_weather = REJECT_UNKNOWN_WEATHER
    
    def validate_risk_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean risk data inputs.
        
        Args:
            data: Raw input data dictionary
            
        Returns:
            Dict with validated and cleaned data
            
        Raises:
            ValidationError: For validation failures with specific error messages
        """
        errors = []
        cleaned_data = {}
        
        # Validate required fields presence
        required_fields = ["crime_index", "accident_rate", "socioeconomic_level", "weather"]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            raise ValidationError("; ".join(errors))
        
        # Validate and clean each field
        try:
            cleaned_data["crime_index"] = self._validate_crime_index(data["crime_index"])
        except ValueError as e:
            errors.append(str(e))
        
        try:
            cleaned_data["accident_rate"] = self._validate_accident_rate(data["accident_rate"])
        except ValueError as e:
            errors.append(str(e))
        
        try:
            cleaned_data["socioeconomic_level"] = self._validate_socioeconomic_level(data["socioeconomic_level"])
        except ValueError as e:
            errors.append(str(e))
        
        try:
            cleaned_data["weather"] = self._validate_weather(data["weather"])
        except ValueError as e:
            errors.append(str(e))
        
        # Validate optional city field
        if "city" in data and data["city"] is not None:
            try:
                cleaned_data["city"] = self._validate_city(data["city"])
            except ValueError as e:
                errors.append(str(e))
        
        if errors:
            raise ValidationError("; ".join(errors))
        
        return cleaned_data
    
    def _validate_crime_index(self, value: Any) -> float:
        """
        Validate crime index value.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated float value
            
        Raises:
            ValueError: If validation fails
        """
        try:
            crime_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"crime_index must be a number, got {type(value).__name__}")
        
        if not (self.crime_range[0] <= crime_value <= self.crime_range[1]):
            raise ValueError(
                f"crime_index must be between {self.crime_range[0]} and {self.crime_range[1]}, got {crime_value}"
            )
        
        return crime_value
    
    def _validate_accident_rate(self, value: Any) -> float:
        """
        Validate accident rate value.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated float value
            
        Raises:
            ValueError: If validation fails
        """
        try:
            accident_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"accident_rate must be a number, got {type(value).__name__}")
        
        if not (self.accident_range[0] <= accident_value <= self.accident_range[1]):
            raise ValueError(
                f"accident_rate must be between {self.accident_range[0]} and {self.accident_range[1]}, got {accident_value}"
            )
        
        return accident_value
    
    def _validate_socioeconomic_level(self, value: Any) -> float:
        """
        Validate socioeconomic level value.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated float value
            
        Raises:
            ValueError: If validation fails
        """
        try:
            socio_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"socioeconomic_level must be a number, got {type(value).__name__}")
        
        if not (self.socio_range[0] <= socio_value <= self.socio_range[1]):
            raise ValueError(
                f"socioeconomic_level must be between {self.socio_range[0]} and {self.socio_range[1]}, got {socio_value}"
            )
        
        return socio_value
    
    def _validate_weather(self, value: Any) -> str:
        """
        Validate weather category with strict checking.
        
        Args:
            value: Input weather value to validate
            
        Returns:
            Validated weather string
            
        Raises:
            ValueError: If weather category is unknown
        """
        if not isinstance(value, str):
            raise ValueError(f"weather must be a string, got {type(value).__name__}")
        
        weather_str = value.strip()
        
        if not weather_str:
            raise ValueError("weather cannot be empty")
        
        if self.reject_unknown_weather and weather_str not in self.weather_categories:
            raise ValueError(f"Unknown weather: {weather_str}")
        
        return weather_str
    
    def _validate_city(self, value: Any) -> str:
        """
        Validate and clean city name.
        
        Args:
            value: Input city value to validate
            
        Returns:
            Validated and cleaned city string
            
        Raises:
            ValueError: If city validation fails
        """
        if not isinstance(value, str):
            raise ValueError(f"city must be a string, got {type(value).__name__}")
        
        city_cleaned = value.strip()
        
        if not city_cleaned:
            raise ValueError("city cannot be empty or whitespace only")
        
        if len(city_cleaned) > 100:
            raise ValueError("city name cannot exceed 100 characters")
        
        return city_cleaned


class CSVValidator:
    """
    Validates CSV data structure and content.
    
    Provides validation for CSV files including column structure,
    data types, and batch validation capabilities.
    """
    
    def __init__(self):
        """Initialize CSV validator."""
        self.risk_validator = RiskDataValidator()
        self.required_columns = CSV_REQUIRED_COLUMNS
    
    def validate_csv_structure(self, df: pd.DataFrame) -> List[str]:
        """
        Validate CSV file structure.
        
        Args:
            df: Pandas DataFrame to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check if DataFrame is empty
        if df.empty:
            errors.append("CSV file is empty")
            return errors
        
        # Check for duplicate column names first (higher priority error)
        duplicate_columns = df.columns[df.columns.duplicated()].tolist()
        if duplicate_columns:
            errors.append(f"Duplicate column names: {', '.join(duplicate_columns)}")
        
        # Check for required columns
        missing_columns = set(self.required_columns) - set(df.columns)
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check for completely empty rows (all NaN)
        empty_rows = df.isnull().all(axis=1).sum()
        if empty_rows > 0:
            errors.append(f"Found {empty_rows} completely empty rows")
        
        return errors
    
    def validate_csv_row(self, row: pd.Series, row_index: int) -> Dict[str, Any]:
        """
        Validate a single CSV row.
        
        Args:
            row: Pandas Series representing a single row
            row_index: Row index for error reporting
            
        Returns:
            Dict with 'status', 'data' (if successful), or 'error' (if failed)
        """
        try:
            # Convert Series to dictionary
            row_data = row.to_dict()
            
            # Handle NaN values
            for key, value in row_data.items():
                if pd.isna(value):
                    row_data[key] = None
            
            # Validate using risk data validator
            validated_data = self.risk_validator.validate_risk_data(row_data)
            
            return {
                "status": "SUCCESS",
                "data": validated_data
            }
            
        except ValidationError as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "row_index": row_index
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "error": f"Unexpected validation error: {str(e)}",
                "row_index": row_index
            }
    
    def get_validation_summary(self, results: List[Dict]) -> Dict[str, int]:
        """
        Generate validation summary statistics.
        
        Args:
            results: List of validation results from validate_csv_row
            
        Returns:
            Dict with success/error counts
        """
        total_rows = len(results)
        success_count = sum(1 for result in results if result["status"] == "SUCCESS")
        error_count = total_rows - success_count
        
        return {
            "total_rows": total_rows,
            "successful_rows": success_count,
            "error_rows": error_count
        }