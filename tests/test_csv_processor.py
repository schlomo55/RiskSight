"""
Comprehensive tests for the CSV Processing Service.

Tests include multi-threaded processing, error handling, batch processing
with mixed data, processing statistics, and CSV structure validation.
"""

import pytest
import pandas as pd
import io
import time
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from services.csv_processor import CSVProcessor, CSVProcessingError
from core.risk_processor import RiskProcessor
from core.validators import ValidationError
from services.logger_service import LoggerService


class TestCSVProcessorInitialization:
    """Test CSV processor initialization and configuration."""
    
    def test_initialization_with_risk_processor(self):
        """Test CSV processor initializes with risk processor dependency."""
        risk_processor = RiskProcessor(noise_level=0.0)
        csv_processor = CSVProcessor(risk_processor)
        
        assert csv_processor.risk_processor == risk_processor
        assert hasattr(csv_processor, 'csv_validator')
        assert hasattr(csv_processor, 'logger')
        assert csv_processor.max_workers == 8  # Default from constants
    
    def test_get_processing_info(self):
        """Test processor info method returns configuration details."""
        risk_processor = RiskProcessor(noise_level=0.0)
        csv_processor = CSVProcessor(risk_processor)
        
        info = csv_processor.get_processing_info()
        
        assert "max_workers" in info
        assert "required_columns" in info
        assert "optional_columns" in info
        assert "output_columns" in info
        assert "risk_processor_info" in info
        
        assert info["max_workers"] == 8
        assert "crime_index" in info["required_columns"]
        assert "city" in info["optional_columns"]
    
    def test_set_worker_count(self):
        """Test setting custom worker count."""
        risk_processor = RiskProcessor(noise_level=0.0)
        csv_processor = CSVProcessor(risk_processor)
        
        # Test valid worker count
        csv_processor.set_worker_count(4)
        assert csv_processor.max_workers == 4
        
        # Test boundary values
        csv_processor.set_worker_count(1)
        assert csv_processor.max_workers == 1
        
        csv_processor.set_worker_count(16)
        assert csv_processor.max_workers == 16
        
        # Test invalid worker count
        with pytest.raises(ValueError, match="Worker count must be between 1 and 16"):
            csv_processor.set_worker_count(0)
        
        with pytest.raises(ValueError, match="Worker count must be between 1 and 16"):
            csv_processor.set_worker_count(20)


class TestCSVStructureValidation:
    """Test CSV structure validation and error detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_processor = RiskProcessor(noise_level=0.0)
        self.csv_processor = CSVProcessor(self.risk_processor)
    
    def test_valid_csv_structure(self):
        """Test validation of properly structured CSV."""
        valid_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
New York,7.5,6.2,4,Rainy
Los Angeles,5.8,8.1,6,Clear
Chicago,8.2,7.3,3,Stormy"""
        
        errors = self.csv_processor.validate_csv_structure(valid_csv)
        assert len(errors) == 0
    
    def test_missing_required_columns(self):
        """Test detection of missing required columns."""
        invalid_csv = """city,crime_index,weather
New York,7.5,Rainy
Los Angeles,5.8,Clear"""
        
        errors = self.csv_processor.validate_csv_structure(invalid_csv)
        assert len(errors) > 0
        assert any("Missing required columns" in error for error in errors)
        assert any("accident_rate" in error for error in errors)
        assert any("socioeconomic_level" in error for error in errors)
    
    def test_empty_csv_file(self):
        """Test handling of empty CSV files."""
        empty_csv = ""
        
        errors = self.csv_processor.validate_csv_structure(empty_csv)
        assert len(errors) > 0
        assert any("empty" in error.lower() for error in errors)
    
    def test_csv_with_only_headers(self):
        """Test CSV with headers but no data rows."""
        headers_only_csv = "city,crime_index,accident_rate,socioeconomic_level,weather"
        
        errors = self.csv_processor.validate_csv_structure(headers_only_csv)
        assert len(errors) > 0
        assert any("empty" in error.lower() for error in errors)
    
    def test_duplicate_column_names(self):
        """Test detection of duplicate column names."""
        duplicate_csv = """city,crime_index,crime_index,socioeconomic_level,weather
New York,7.5,6.2,4,Rainy"""
        
        errors = self.csv_processor.validate_csv_structure(duplicate_csv)
        assert len(errors) > 0
        assert any("Duplicate column names" in error for error in errors)


class TestCSVRowProcessing:
    """Test individual row processing and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_processor = RiskProcessor(noise_level=0.0)
        self.csv_processor = CSVProcessor(self.risk_processor)
    
    def test_valid_row_processing(self):
        """Test processing of valid data rows."""
        valid_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
New York,7.5,6.2,4,Rainy"""
        
        result_df = self.csv_processor.process_csv_file(valid_csv, "test.csv")
        
        # Should have one row with success status
        assert len(result_df) == 1
        assert result_df.iloc[0]["processing_status"] == "SUCCESS"
        assert result_df.iloc[0]["error_message"] == ""
        
        # Should have calculated risk scores
        assert pd.notna(result_df.iloc[0]["risk_score"])
        assert pd.notna(result_df.iloc[0]["crime_index_component"])
        assert pd.notna(result_df.iloc[0]["accident_rate_component"])
        assert pd.notna(result_df.iloc[0]["socioeconomic_level_component"])
        assert pd.notna(result_df.iloc[0]["weather_component"])
    
    def test_invalid_weather_row_processing(self):
        """Test processing of rows with invalid weather."""
        invalid_weather_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Boston,5.0,4.0,6,Foggy"""
        
        result_df = self.csv_processor.process_csv_file(invalid_weather_csv, "test.csv")
        
        # Should have one row with error status
        assert len(result_df) == 1
        assert result_df.iloc[0]["processing_status"] == "ERROR"
        assert "Unknown weather: Foggy" in result_df.iloc[0]["error_message"]
        
        # Score columns should be blank
        assert result_df.iloc[0]["risk_score"] == ""
        assert result_df.iloc[0]["crime_index_component"] == ""
        assert result_df.iloc[0]["accident_rate_component"] == ""
        assert result_df.iloc[0]["socioeconomic_level_component"] == ""
        assert result_df.iloc[0]["weather_component"] == ""
    
    def test_out_of_range_values_row_processing(self):
        """Test processing of rows with out-of-range values."""
        out_of_range_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Seattle,15.0,5.0,6,Clear"""  # crime_index > 10
        
        result_df = self.csv_processor.process_csv_file(out_of_range_csv, "test.csv")
        
        assert len(result_df) == 1
        assert result_df.iloc[0]["processing_status"] == "ERROR"
        assert "crime_index must be between 0 and 10" in result_df.iloc[0]["error_message"]
        
        # Score columns should be blank
        assert result_df.iloc[0]["risk_score"] == ""
    
    def test_missing_values_row_processing(self):
        """Test processing of rows with missing values."""
        missing_values_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Denver,,5.0,6,Clear"""  # Missing crime_index
        
        result_df = self.csv_processor.process_csv_file(missing_values_csv, "test.csv")
        
        assert len(result_df) == 1
        assert result_df.iloc[0]["processing_status"] == "ERROR"
        # Error message should indicate missing field
        assert "crime_index" in result_df.iloc[0]["error_message"].lower()
    
    def test_invalid_data_types_row_processing(self):
        """Test processing of rows with invalid data types."""
        invalid_types_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Miami,high,5.0,6,Clear"""  # crime_index should be numeric
        
        result_df = self.csv_processor.process_csv_file(invalid_types_csv, "test.csv")
        
        assert len(result_df) == 1
        assert result_df.iloc[0]["processing_status"] == "ERROR"
        assert "must be a number" in result_df.iloc[0]["error_message"]


class TestCSVBatchProcessing:
    """Test batch processing with mixed valid and invalid data."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_processor = RiskProcessor(noise_level=0.0)
        self.csv_processor = CSVProcessor(self.risk_processor)
    
    def test_mixed_valid_invalid_batch(self):
        """Test batch with both valid and invalid rows."""
        mixed_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
New York,7.5,6.2,4,Rainy
Boston,5.0,4.0,6,Foggy
Los Angeles,5.8,8.1,6,Clear
Chicago,15.0,7.3,3,Stormy
Phoenix,4.2,3.8,7,Clear"""
        
        result_df = self.csv_processor.process_csv_file(mixed_csv, "mixed_test.csv")
        
        # Should process all rows
        assert len(result_df) == 5
        
        # Count successful and error rows
        success_rows = result_df[result_df["processing_status"] == "SUCCESS"]
        error_rows = result_df[result_df["processing_status"] == "ERROR"]
        
        assert len(success_rows) == 3  # New York, Los Angeles, Phoenix
        assert len(error_rows) == 2   # Boston (bad weather), Chicago (out of range)
        
        # Verify successful rows have scores
        for _, row in success_rows.iterrows():
            assert pd.notna(row["risk_score"])
            assert row["risk_score"] != ""
            assert row["error_message"] == ""
        
        # Verify error rows have blank scores and error messages
        for _, row in error_rows.iterrows():
            assert row["risk_score"] == ""
            assert row["error_message"] != ""
    
    def test_large_batch_processing(self):
        """Test processing of larger batches for performance."""
        # Create a larger CSV with 100 rows
        rows = ["city,crime_index,accident_rate,socioeconomic_level,weather"]
        
        for i in range(100):
            city = f"City_{i:03d}"
            crime = 5.0 + (i % 5)  # Vary between 5.0 and 9.0
            accident = 3.0 + (i % 6)  # Vary between 3.0 and 8.0
            socio = 2 + (i % 8)  # Vary between 2 and 9
            weather = ["Clear", "Rainy", "Snowy", "Stormy"][i % 4]
            rows.append(f"{city},{crime},{accident},{socio},{weather}")
        
        large_csv = "\n".join(rows)
        
        start_time = time.time()
        result_df = self.csv_processor.process_csv_file(large_csv, "large_test.csv")
        processing_time = time.time() - start_time
        
        # Should process all rows
        assert len(result_df) == 100
        
        # All rows should be successful (all values are valid)
        success_count = len(result_df[result_df["processing_status"] == "SUCCESS"])
        assert success_count == 100
        
        # Processing should be reasonably fast (multi-threaded)
        assert processing_time < 10.0  # Should complete within 10 seconds
    
    def test_all_error_rows_batch(self):
        """Test batch where all rows have errors."""
        all_errors_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
City1,15.0,5.0,6,Clear
City2,5.0,4.0,6,Foggy  
City3,5.0,15.0,6,Clear
City4,5.0,4.0,0,Clear"""
        
        result_df = self.csv_processor.process_csv_file(all_errors_csv, "errors_test.csv")
        
        # Should process all rows
        assert len(result_df) == 4
        
        # All should be errors
        error_count = len(result_df[result_df["processing_status"] == "ERROR"])
        assert error_count == 4
        
        # All should have blank scores
        for _, row in result_df.iterrows():
            assert row["risk_score"] == ""
            assert row["error_message"] != ""


class TestCSVProcessingStatistics:
    """Test processing statistics and logging accuracy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_processor = RiskProcessor(noise_level=0.0)
        self.csv_processor = CSVProcessor(self.risk_processor)
    
    @patch.object(LoggerService, 'log_csv_processing_summary')
    @patch.object(LoggerService, 'log_error')
    def test_processing_statistics_accuracy(self, mock_log_error, mock_log_summary):
        """Test that processing statistics are accurately calculated and logged."""
        mixed_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Valid1,5.0,4.0,6,Clear
Invalid1,5.0,4.0,6,Foggy
Valid2,6.0,3.0,7,Rainy
Invalid2,15.0,4.0,6,Clear
Valid3,4.0,5.0,8,Snowy"""
        
        result_df = self.csv_processor.process_csv_file(mixed_csv, "stats_test.csv")
        
        # Verify summary was logged with correct statistics
        mock_log_summary.assert_called_once()
        call_args = mock_log_summary.call_args[0]
        
        total_rows, success_count, error_count, processing_time = call_args
        assert total_rows == 5
        assert success_count == 3
        assert error_count == 2
        assert processing_time > 0
        
        # Verify individual errors were logged
        assert mock_log_error.call_count == 2  # Two error rows
    
    def test_processing_time_measurement(self):
        """Test that processing time is measured and reasonable."""
        simple_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Test1,5.0,4.0,6,Clear
Test2,6.0,5.0,7,Rainy"""
        
        start_time = time.time()
        result_df = self.csv_processor.process_csv_file(simple_csv, "time_test.csv")
        actual_time = time.time() - start_time
        
        # Processing should complete quickly for small datasets
        assert actual_time < 5.0
        
        # Results should be complete
        assert len(result_df) == 2
        assert all(result_df["processing_status"] == "SUCCESS")


class TestCSVProcessingMultithreading:
    """Test multi-threaded processing behavior and thread safety."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_processor = RiskProcessor(noise_level=0.0)
        self.csv_processor = CSVProcessor(self.risk_processor)
    
    def test_multithreading_with_custom_worker_count(self):
        """Test processing with different worker counts."""
        test_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
City1,5.0,4.0,6,Clear
City2,6.0,5.0,7,Rainy
City3,7.0,6.0,5,Snowy
City4,4.0,3.0,8,Stormy"""
        
        # Test with different worker counts
        for worker_count in [1, 2, 4]:
            self.csv_processor.set_worker_count(worker_count)
            
            result_df = self.csv_processor.process_csv_file(test_csv, f"worker_{worker_count}_test.csv")
            
            # Results should be identical regardless of worker count
            assert len(result_df) == 4
            assert all(result_df["processing_status"] == "SUCCESS")
            
            # All rows should have calculated scores
            for _, row in result_df.iterrows():
                assert pd.notna(row["risk_score"])
                assert row["risk_score"] != ""
    
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_thread_pool_executor_usage(self, mock_executor_class):
        """Test that ThreadPoolExecutor is used correctly."""
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        mock_executor.submit.return_value = Mock()
        
        # Create mock futures
        mock_futures = []
        for i in range(2):
            mock_future = Mock()
            mock_future.result.return_value = {
                "status": "SUCCESS",
                "data": {
                    "risk_score": 50.0,
                    "crime_index_component": 50.0,
                    "accident_rate_component": 40.0,
                    "socioeconomic_level_component": 60.0,
                    "weather_component": 10.0
                }
            }
            mock_futures.append(mock_future)
        
        # Mock as_completed to return our mock futures
        with patch('concurrent.futures.as_completed', return_value=mock_futures):
            test_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
City1,5.0,4.0,6,Clear
City2,6.0,5.0,7,Rainy"""
            
            result_df = self.csv_processor.process_csv_file(test_csv, "thread_test.csv")
            
            # Verify ThreadPoolExecutor was created with correct max_workers
            mock_executor_class.assert_called_once_with(max_workers=self.csv_processor.max_workers)
            
            # Verify submit was called for each row
            assert mock_executor.submit.call_count == 2


class TestCSVProcessingErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_processor = RiskProcessor(noise_level=0.0)
        self.csv_processor = CSVProcessor(self.risk_processor)
    
    def test_csv_parsing_errors(self):
        """Test handling of CSV parsing errors."""
        # Malformed CSV
        malformed_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
New York,7.5,6.2,4,Rainy
Los Angeles,5.8,8.1,6,Clear,Extra,Columns"""
        
        # Should handle gracefully and process valid rows
        result_df = self.csv_processor.process_csv_file(malformed_csv, "malformed_test.csv")
        
        # Should still process the valid rows
        assert len(result_df) >= 1
    
    def test_concurrent_processing_exception_handling(self):
        """Test handling of exceptions during concurrent processing."""
        # Mock the risk processor to raise an exception for specific input
        with patch.object(self.risk_processor, 'process_risk_data', 
                         side_effect=Exception("Simulated processing error")):
            
            test_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
City1,5.0,4.0,6,Clear"""
            
            result_df = self.csv_processor.process_csv_file(test_csv, "exception_test.csv")
            
            # Should handle the exception and mark row as error
            assert len(result_df) == 1
            assert result_df.iloc[0]["processing_status"] == "ERROR"
            assert "processing error" in result_df.iloc[0]["error_message"].lower()
    
    def test_structural_csv_errors(self):
        """Test handling of structural CSV problems."""
        # Test empty file content
        with pytest.raises(CSVProcessingError, match="CSV file contains no data"):
            self.csv_processor.process_csv_file("", "empty_test.csv")
        
        # Test invalid CSV structure (missing required columns)
        invalid_structure_csv = """city,weather
New York,Rainy"""
        
        with pytest.raises(CSVProcessingError, match="CSV structural errors"):
            self.csv_processor.process_csv_file(invalid_structure_csv, "invalid_structure_test.csv")


class TestCSVOutputFormat:
    """Test CSV output format and column structure."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_processor = RiskProcessor(noise_level=0.0)
        self.csv_processor = CSVProcessor(self.risk_processor)
    
    def test_output_column_structure(self):
        """Test that output CSV has all required columns."""
        test_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Test City,5.0,4.0,6,Clear"""
        
        result_df = self.csv_processor.process_csv_file(test_csv, "output_test.csv")
        
        # Check for all expected output columns
        expected_columns = [
            "city", "crime_index", "accident_rate", "socioeconomic_level", "weather",
            "risk_score", "crime_index_component", "accident_rate_component", 
            "socioeconomic_level_component", "weather_component",
            "processing_status", "error_message"
        ]
        
        for col in expected_columns:
            assert col in result_df.columns, f"Missing column: {col}"
    
    def test_output_without_optional_city_column(self):
        """Test processing CSV without optional city column."""
        no_city_csv = """crime_index,accident_rate,socioeconomic_level,weather
5.0,4.0,6,Clear
6.0,5.0,7,Rainy"""
        
        result_df = self.csv_processor.process_csv_file(no_city_csv, "no_city_test.csv")
        
        # Should still process successfully
        assert len(result_df) == 2
        assert all(result_df["processing_status"] == "SUCCESS")
        
        # City column should be present but empty or filled with default
        assert "city" in result_df.columns
    
    def test_component_score_precision(self):
        """Test that component scores maintain appropriate precision."""
        test_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Precision Test,7.33,4.67,5,Clear"""
        
        result_df = self.csv_processor.process_csv_file(test_csv, "precision_test.csv")
        
        # Check that scores are properly formatted (should be numeric)
        row = result_df.iloc[0]
        
        # Should be able to convert score columns to float
        assert isinstance(float(row["risk_score"]), float)
        assert isinstance(float(row["crime_index_component"]), float)
        assert isinstance(float(row["accident_rate_component"]), float)
        assert isinstance(float(row["socioeconomic_level_component"]), float)
        assert isinstance(float(row["weather_component"]), float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])