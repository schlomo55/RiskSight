"""
Configuration constants for the Risk Processing Engine.

All system tunables are centralized in this file to enable easy modification
without code changes. This includes weights, rules, validation ranges,
CSV processing settings, and logging configuration.
"""

from typing import Dict, List, Set, Tuple

# Risk Engine Configuration
DEFAULT_WEIGHTS: Dict[str, float] = {
    "crime_index": 0.30,
    "accident_rate": 0.25,
    "socioeconomic_level": 0.25,
    "weather": 0.20
}

# Weather Categories with Component Scores (0-1 scale)
# Maps weather condition to risk component score
WEATHER_CATEGORIES: Dict[str, float] = {
    "Clear": 0.10,
    "Rainy": 0.50,
    "Snowy": 0.70,
    "Stormy": 0.90,
    "Extreme": 0.95,
}

# Extensible Amplification Rules
# Add or remove rules freely here without code changes
# Supports comparison operators (">7", "<3") and set membership checks
DEFAULT_RULES: List[Dict] = [
    {
        "conditions": {
            "crime_index": ">7", 
            "weather": {"Stormy", "Snowy", "Extreme"}
        }, 
        "multiplier": 1.15,
        "description": "High crime + severe weather amplification"
    },
    {
        "conditions": {
            "crime_index": "<4", 
            "weather": {"Clear"}
        }, 
        "multiplier": 0.9,
        "description": "Low crime + clear weather bonus (risk reduction)"
    }
    # Additional rules can be added here following the same pattern
]

# Risk Processing Configuration
DEFAULT_NOISE_LEVEL: float = 0.05  # Set to 0.0 for deterministic tests
OUTPUT_SCALE: int = 100  # Final risk score scale (0-100)
REJECT_UNKNOWN_WEATHER: bool = True  # Strict weather validation

# Input Validation Ranges
CRIME_RANGE: Tuple[int, int] = (0, 10)
ACCIDENT_RANGE: Tuple[int, int] = (0, 10)
SOCIO_RANGE: Tuple[int, int] = (1, 10)

# CSV Processing Configuration
CSV_REQUIRED_COLUMNS: List[str] = [
    "crime_index", 
    "accident_rate", 
    "socioeconomic_level", 
    "weather"
]

CSV_OPTIONAL_COLUMNS: List[str] = ["city"]

CSV_OUTPUT_COLUMNS: List[str] = [
    # Input columns
    "city", "crime_index", "accident_rate", "socioeconomic_level", "weather",
    # Calculated component columns
    "crime_index_component", "accident_rate_component", 
    "socioeconomic_level_component", "weather_component",
    # Status columns
    "processing_status", "error_message", "risk_score"
]

# CSV Processing Performance Settings
CSV_MAX_WORKERS: int = 8  # ThreadPoolExecutor worker count
CSV_CHUNK_SIZE: int = 20000  # Rows per processing chunk

# Logging Configuration
GENERAL_LOG_PATH: str = "logs/general.log"
ERROR_LOG_PATH: str = "logs/error.log"
LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S"  # ISO-8601 format

# API Configuration
API_TITLE: str = "Risk Processing API"
API_VERSION: str = "1.0.0"
API_DESCRIPTION: str = """
Risk Processing API for transforming raw risk indicators into normalized risk scores.

Supports both single JSON requests and batch CSV processing with comprehensive
error handling and logging.
"""

# System Constants
SUPPORTED_FILE_EXTENSIONS: Set[str] = {".csv"}
MAX_UPLOAD_SIZE_MB: int = 100  # Maximum CSV file size in MB