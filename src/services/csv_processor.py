"""
CSV processing service with multi-threading and comprehensive error handling.

Handles batch processing of CSV files with concurrent processing,
per-row error tracking, and detailed logging of processing statistics.
Error rows are retained in output with proper status indicators.
"""

import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from io import StringIO

from src.core.risk_processor import RiskProcessor
from src.core.validators import CSVValidator, ValidationError
from src.services.logger_service import LoggerService
from src.config.constants import (
    CSV_MAX_WORKERS, CSV_OUTPUT_COLUMNS, CSV_REQUIRED_COLUMNS, CSV_OPTIONAL_COLUMNS
)


class CSVProcessingError(Exception):
    """Custom exception for CSV processing errors."""
    pass


class CSVProcessor:
    """
    Handles concurrent CSV processing with comprehensive error tracking.
    
    Features:
    - Multi-threaded processing with configurable worker count
    - Per-row error handling without batch failure
    - Error rows retained in output with status indicators
    - Detailed logging of processing statistics
    - Comprehensive validation and error reporting
    - Memory-efficient processing for files up to 100MB
    """
    
    def __init__(self, risk_processor: RiskProcessor):
        """
        Initialize CSV processor with risk processing engine.
        
        Args:
            risk_processor: Configured risk processor instance
        """
        self.risk_processor = risk_processor
        self.csv_validator = CSVValidator()
        self.logger = LoggerService()
        self.max_workers = CSV_MAX_WORKERS
    
    def process_csv_file(self, file_content: str, filename: Optional[str] = None) -> pd.DataFrame:
        """
        Process CSV file content with multi-threading and error handling.
        
        Args:
            file_content: CSV file content as string
            filename: Optional filename for logging purposes
            
        Returns:
            DataFrame with processing results including error tracking
            
        Raises:
            CSVProcessingError: For structural CSV errors
        """
        start_time = time.time()
        filename_display = filename or "uploaded_file"
        
        self.logger.log_processing_start(
            f"CSV processing: {filename_display}",
            {"max_workers": self.max_workers}
        )
        
        try:
            # Parse CSV content
            df = self._parse_csv_content(file_content, filename_display)
            
            # Validate CSV structure
            structural_errors = self.csv_validator.validate_csv_structure(df)
            if structural_errors:
                error_msg = f"CSV structural errors: {'; '.join(structural_errors)}"
                self.logger.log_error(f"CSV validation failed for {filename_display}: {error_msg}")
                raise CSVProcessingError(error_msg)
            
            # Process rows with multi-threading
            result_df = self._process_rows_concurrent(df, filename_display)
            
            # Calculate processing statistics
            processing_time = time.time() - start_time
            total_rows = len(result_df)
            error_count = len(result_df[result_df['processing_status'] == 'ERROR'])
            success_count = total_rows - error_count
            
            # Log processing summary
            self.logger.log_csv_processing_summary(
                total_rows, success_count, error_count, processing_time
            )
            
            self.logger.log_processing_complete(
                f"CSV processing: {filename_display}",
                {
                    "total_rows": total_rows,
                    "successful_rows": success_count,
                    "error_rows": error_count,
                    "processing_time_seconds": round(processing_time, 2)
                }
            )
            
            return result_df
            
        except CSVProcessingError:
            # Re-raise CSV processing errors as-is
            raise
        except Exception as e:
            error_msg = f"Unexpected CSV processing error: {str(e)}"
            self.logger.log_error(f"CSV processing failed for {filename_display}", e)
            raise CSVProcessingError(error_msg)
    
    def _parse_csv_content(self, content: str, filename: str) -> pd.DataFrame:
        """
        Parse CSV content into DataFrame with proper error handling.
        
        Args:
            content: Raw CSV content string
            filename: Filename for error reporting
            
        Returns:
            Parsed DataFrame
            
        Raises:
            CSVProcessingError: If parsing fails
        """
        try:
            # Parse CSV with pandas
            df = pd.read_csv(StringIO(content))
            
            if df.empty:
                raise CSVProcessingError("CSV file is empty")
            
            self.logger.log_info(
                f"Parsed CSV file: {filename}",
                {
                    "rows": len(df),
                    "columns": list(df.columns)
                }
            )
            
            return df
            
        except pd.errors.EmptyDataError:
            raise CSVProcessingError("CSV file contains no data")
        except pd.errors.ParserError as e:
            raise CSVProcessingError(f"CSV parsing error: {str(e)}")
        except Exception as e:
            raise CSVProcessingError(f"Failed to parse CSV: {str(e)}")
    
    def _process_rows_concurrent(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """
        Process DataFrame rows concurrently with error handling.
        
        Args:
            df: Input DataFrame to process
            filename: Filename for logging purposes
            
        Returns:
            DataFrame with processing results and error tracking
        """
        total_rows = len(df)
        self.logger.log_info(
            f"Starting concurrent processing: {filename}",
            {
                "total_rows": total_rows,
                "workers": self.max_workers
            }
        )
        
        # Initialize result DataFrame with output structure
        result_df = self._initialize_result_dataframe(df)
        
        # Track errors for logging
        row_errors = []
        
        # Process rows with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all rows for processing
            future_to_index = {
                executor.submit(self._process_single_row, row, idx): idx
                for idx, row in df.iterrows()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                row_idx = future_to_index[future]
                
                try:
                    row_result = future.result()
                    self._update_result_row(result_df, row_idx, row_result)
                    
                    # Log individual row errors
                    if row_result["status"] == "ERROR":
                        error_info = {
                            "row": row_idx + 1,
                            "error": row_result["error"]
                        }
                        row_errors.append(error_info)
                        self.logger.log_error(f"Row {row_idx + 1}: {row_result['error']}")
                        
                except Exception as e:
                    # Handle unexpected processing errors
                    error_msg = f"Unexpected processing error: {str(e)}"
                    error_result = {
                        "status": "ERROR",
                        "error": error_msg
                    }
                    self._update_result_row(result_df, row_idx, error_result)
                    
                    error_info = {
                        "row": row_idx + 1,
                        "error": error_msg
                    }
                    row_errors.append(error_info)
                    self.logger.log_error(f"Row {row_idx + 1}: {error_msg}", e)
        
        return result_df
    
    def _initialize_result_dataframe(self, input_df: pd.DataFrame) -> pd.DataFrame:
        """
        Initialize result DataFrame with proper column structure.
        
        Args:
            input_df: Input DataFrame
            
        Returns:
            Initialized result DataFrame with all required columns
        """
        # Start with copy of input data
        result_df = input_df.copy()
        
        # Add missing optional columns if not present
        for optional_col in CSV_OPTIONAL_COLUMNS:
            if optional_col not in result_df.columns:
                result_df[optional_col] = ""
        
        # Initialize all output columns
        output_columns = [
            "risk_score", "crime_index_component", "accident_rate_component",
            "socioeconomic_level_component", "weather_component"
        ]
        
        for col in output_columns:
            result_df[col] = ""
        
        # Initialize status tracking columns
        result_df["processing_status"] = "SUCCESS"
        result_df["error_message"] = ""
        
        # Reorder columns to match expected output format
        column_order = []
        for col in CSV_OUTPUT_COLUMNS:
            if col in result_df.columns:
                column_order.append(col)
        
        # Add any remaining columns not in the standard output
        for col in result_df.columns:
            if col not in column_order:
                column_order.append(col)
        
        return result_df[column_order]
    
    def _process_single_row(self, row: pd.Series, row_index: int) -> Dict[str, Any]:
        """
        Process a single CSV row and return result with status.
        
        Args:
            row: Pandas Series representing a single row
            row_index: Row index for error reporting
            
        Returns:
            Dict with processing status and results or error information
        """
        try:
            # Convert row to dictionary and handle NaN values
            row_data = row.to_dict()
            
            # Replace NaN values with None for proper validation
            for key, value in row_data.items():
                if pd.isna(value):
                    row_data[key] = None
            
            # Process the risk data using the risk processor
            result = self.risk_processor.process_risk_data(row_data)
            
            return {
                "status": "SUCCESS",
                "data": result
            }
            
        except ValidationError as e:
            return {
                "status": "ERROR",
                "error": str(e)
            }
        except ValueError as e:
            return {
                "status": "ERROR",
                "error": str(e)
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "error": f"Unexpected row processing error: {str(e)}"
            }
    
    def _update_result_row(self, result_df: pd.DataFrame, row_idx: int, row_result: Dict[str, Any]):
        """
        Update result DataFrame with processing results for a specific row.
        
        Args:
            result_df: Result DataFrame to update
            row_idx: Row index to update
            row_result: Processing result for the row
        """
        if row_result["status"] == "SUCCESS":
            # Update successful row with calculated values
            data = row_result["data"]
            
            result_df.at[row_idx, "risk_score"] = data.get("risk_score", "")
            result_df.at[row_idx, "crime_index_component"] = data.get("crime_index_component", "")
            result_df.at[row_idx, "accident_rate_component"] = data.get("accident_rate_component", "")
            result_df.at[row_idx, "socioeconomic_level_component"] = data.get("socioeconomic_level_component", "")
            result_df.at[row_idx, "weather_component"] = data.get("weather_component", "")
            result_df.at[row_idx, "processing_status"] = "SUCCESS"
            result_df.at[row_idx, "error_message"] = ""
            
        else:
            # Update error row with blank scores and error information
            result_df.at[row_idx, "risk_score"] = ""
            result_df.at[row_idx, "crime_index_component"] = ""
            result_df.at[row_idx, "accident_rate_component"] = ""
            result_df.at[row_idx, "socioeconomic_level_component"] = ""
            result_df.at[row_idx, "weather_component"] = ""
            result_df.at[row_idx, "processing_status"] = "ERROR"
            result_df.at[row_idx, "error_message"] = row_result["error"]
    
    def validate_csv_structure(self, file_content: str) -> List[str]:
        """
        Validate CSV file structure without processing data.
        
        Args:
            file_content: CSV file content as string
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            df = pd.read_csv(StringIO(file_content))
            return self.csv_validator.validate_csv_structure(df)
        except Exception as e:
            return [f"Failed to parse CSV for validation: {str(e)}"]
    
    def get_processing_info(self) -> Dict[str, Any]:
        """
        Get information about the CSV processor configuration.
        
        Returns:
            Dictionary with processor configuration details
        """
        return {
            "max_workers": self.max_workers,
            "required_columns": CSV_REQUIRED_COLUMNS.copy(),
            "optional_columns": CSV_OPTIONAL_COLUMNS.copy(),
            "output_columns": CSV_OUTPUT_COLUMNS.copy(),
            "risk_processor_info": self.risk_processor.get_processor_info()
        }
    
    def set_worker_count(self, worker_count: int):
        """
        Set the number of worker threads for processing.
        
        Args:
            worker_count: Number of worker threads (1-16)
        """
        if 1 <= worker_count <= 16:
            self.max_workers = worker_count
            self.logger.log_info(f"Updated CSV processor worker count to {worker_count}")
        else:
            raise ValueError("Worker count must be between 1 and 16")