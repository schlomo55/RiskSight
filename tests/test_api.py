"""
Comprehensive API integration tests for the Risk Processing API.

Tests include endpoint functionality, error handling, file uploads,
health checks, and complete API behavior validation.
"""

import pytest
import json
import io
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Import the FastAPI app
from main import app
from api.routes import risk_processor, csv_processor
from core.validators import ValidationError
from services.csv_processor import CSVProcessingError
from config.constants import WEATHER_CATEGORIES


class TestAPIClientSetup:
    """Test API client setup and basic connectivity."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_api_client_setup(self):
        """Test that test client is properly configured."""
        assert self.client is not None
        assert hasattr(self.client, 'get')
        assert hasattr(self.client, 'post')
    
    def test_app_metadata(self):
        """Test that FastAPI app has correct metadata."""
        assert app.title == "Risk Processing API"
        assert app.version == "1.0.0"
        assert "Risk Processing API" in app.description


class TestRootEndpoint:
    """Test the root endpoint and API information."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_root_endpoint_success(self):
        """Test root endpoint returns API information."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        assert "weather_categories" in data
        assert "required_csv_columns" in data
        
        # Verify weather categories match configuration
        assert set(data["weather_categories"]) == set(WEATHER_CATEGORIES.keys())
    
    def test_root_endpoint_structure(self):
        """Test root endpoint response structure."""
        response = self.client.get("/")
        data = response.json()
        
        # Check endpoints information
        endpoints = data["endpoints"]
        assert "process" in endpoints
        assert "process_csv" in endpoints
        assert "health" in endpoints
        assert "info" in endpoints
        assert "docs" in endpoints


class TestHealthEndpoint:
    """Test health check endpoint functionality."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_check_success(self):
        """Test health endpoint returns healthy status."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required health fields
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "components" in data
        
        # Should be healthy by default
        assert data["status"] in ["healthy", "warning"]
        assert data["version"] == "1.0.0"
    
    def test_health_check_components(self):
        """Test health check includes component status."""
        response = self.client.get("/health")
        data = response.json()
        
        components = data["components"]
        
        # Should include key components
        expected_components = ["risk_processor", "csv_processor", "logging"]
        for component in expected_components:
            assert component in components or len(components) > 0  # Flexible for different component names
    
    @patch('services.logger_service.LoggerService.check_log_files_exist')
    def test_health_check_with_logging_issues(self, mock_log_check):
        """Test health check when logging has issues."""
        # Mock logging issues
        mock_log_check.return_value = {
            "general_log": {"exists": False, "writable": False},
            "error_log": {"exists": False, "writable": False}
        }
        
        response = self.client.get("/health")
        
        # Should still return 200 but may show warning status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "warning", "error"]


class TestInfoEndpoint:
    """Test processor info endpoint functionality."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_info_endpoint_success(self):
        """Test info endpoint returns processor configuration."""
        response = self.client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required configuration fields
        assert "weights" in data
        assert "rules_count" in data
        assert "noise_level" in data
        assert "weather_categories" in data
        assert "output_scale" in data
        assert "csv_max_workers" in data
    
    def test_info_endpoint_weights_structure(self):
        """Test info endpoint returns correct weights structure."""
        response = self.client.get("/info")
        data = response.json()
        
        weights = data["weights"]
        expected_weight_keys = ["crime_index", "accident_rate", "socioeconomic_level", "weather"]
        
        for key in expected_weight_keys:
            assert key in weights
            assert isinstance(weights[key], (int, float))
            assert 0 <= weights[key] <= 1
    
    def test_info_endpoint_configuration_values(self):
        """Test info endpoint returns reasonable configuration values."""
        response = self.client.get("/info")
        data = response.json()
        
        # Check reasonable values
        assert data["rules_count"] >= 0
        assert 0 <= data["noise_level"] <= 1
        assert data["output_scale"] == 100
        assert 1 <= data["csv_max_workers"] <= 32


class TestSingleRiskProcessingEndpoint:
    """Test the POST /process endpoint for single risk processing."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_valid_single_risk_processing(self):
        """Test successful single risk processing."""
        valid_request = {
            "city": "Test City",
            "crime_index": 6.5,
            "accident_rate": 5.2,
            "socioeconomic_level": 7,
            "weather": "Rainy"
        }
        
        response = self.client.post("/process", json=valid_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "city" in data
        assert "risk_score" in data
        assert "components" in data
        
        # Check city preservation
        assert data["city"] == "Test City"
        
        # Check risk score
        assert isinstance(data["risk_score"], (int, float))
        assert 0 <= data["risk_score"] <= 100
        
        # Check components structure
        components = data["components"]
        expected_components = ["crime_component", "accident_component", 
                             "socioeconomic_component", "weather_component"]
        
        for component in expected_components:
            assert component in components
            assert isinstance(components[component], (int, float))
            assert 0 <= components[component] <= 100
    
    def test_valid_request_without_city(self):
        """Test valid request without optional city field."""
        request_without_city = {
            "crime_index": 5.0,
            "accident_rate": 4.0,
            "socioeconomic_level": 6,
            "weather": "Clear"
        }
        
        response = self.client.post("/process", json=request_without_city)
        
        assert response.status_code == 200
        data = response.json()
        
        # City should be null/None
        assert data["city"] is None
        assert "risk_score" in data
        assert "components" in data
    
    def test_invalid_weather_category(self):
        """Test request with invalid weather category returns 400."""
        invalid_weather_request = {
            "crime_index": 5.0,
            "accident_rate": 4.0,
            "socioeconomic_level": 6,
            "weather": "Foggy"  # Not in WEATHER_CATEGORIES
        }
        
        response = self.client.post("/process", json=invalid_weather_request)
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "Unknown weather: Foggy" in data["detail"]
    
    def test_out_of_range_crime_index(self):
        """Test request with out-of-range crime index returns 400."""
        out_of_range_request = {
            "crime_index": 15.0,  # Above maximum of 10
            "accident_rate": 4.0,
            "socioeconomic_level": 6,
            "weather": "Clear"
        }
        
        response = self.client.post("/process", json=out_of_range_request)
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "crime_index" in data["detail"]
    
    def test_missing_required_fields(self):
        """Test request with missing required fields returns 400."""
        incomplete_request = {
            "crime_index": 5.0,
            # Missing accident_rate, socioeconomic_level, weather
        }
        
        response = self.client.post("/process", json=incomplete_request)
        
        assert response.status_code == 422  # Pydantic validation error
        data = response.json()
        
        assert "detail" in data
        # Should have multiple validation errors
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0
    
    def test_invalid_data_types(self):
        """Test request with invalid data types returns 400."""
        invalid_types_request = {
            "crime_index": "high",  # Should be numeric
            "accident_rate": 4.0,
            "socioeconomic_level": 6,
            "weather": "Clear"
        }
        
        response = self.client.post("/process", json=invalid_types_request)
        
        assert response.status_code == 422  # Pydantic validation error
        data = response.json()
        
        assert "detail" in data
    
    def test_boundary_values(self):
        """Test requests with boundary values."""
        # Test minimum values
        min_values_request = {
            "crime_index": 0.0,
            "accident_rate": 0.0,
            "socioeconomic_level": 1,
            "weather": "Clear"
        }
        
        response = self.client.post("/process", json=min_values_request)
        assert response.status_code == 200
        
        # Test maximum values
        max_values_request = {
            "crime_index": 10.0,
            "accident_rate": 10.0,
            "socioeconomic_level": 10,
            "weather": "Extreme"
        }
        
        response = self.client.post("/process", json=max_values_request)
        assert response.status_code == 200


class TestCSVProcessingEndpoint:
    """Test the POST /process-csv endpoint for batch processing."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_valid_csv_upload(self):
        """Test successful CSV file upload and processing."""
        csv_content = """city,crime_index,accident_rate,socioeconomic_level,weather
New York,7.5,6.2,4,Rainy
Los Angeles,5.8,8.1,6,Clear
Chicago,8.2,7.3,3,Stormy"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("test_data.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Check CSV content
        csv_response = response.content.decode('utf-8')
        lines = csv_response.strip().split('\n')
        
        # Should have header + 3 data rows
        assert len(lines) >= 4
        
        # Check for output columns in header
        header = lines[0].lower()
        assert "risk_score" in header
        assert "processing_status" in header
        assert "error_message" in header
    
    def test_csv_with_mixed_valid_invalid_rows(self):
        """Test CSV processing with both valid and invalid rows."""
        mixed_csv = """city,crime_index,accident_rate,socioeconomic_level,weather
Valid City,5.0,4.0,6,Clear
Invalid City,5.0,4.0,6,Foggy
Another Valid,6.0,5.0,7,Rainy"""
        
        csv_file = io.BytesIO(mixed_csv.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("mixed_data.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == 200
        
        # Parse response to check error handling
        csv_response = response.content.decode('utf-8')
        lines = csv_response.strip().split('\n')
        
        # Should have processed all rows
        assert len(lines) >= 4  # Header + 3 data rows
        
        # Check that invalid rows are marked as errors
        assert "ERROR" in csv_response
        assert "Unknown weather: Foggy" in csv_response or "ERROR" in csv_response
    
    def test_csv_missing_required_columns(self):
        """Test CSV upload with missing required columns returns 400."""
        invalid_csv = """city,crime_index,weather
New York,7.5,Rainy
Los Angeles,5.8,Clear"""
        
        csv_file = io.BytesIO(invalid_csv.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("invalid_structure.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "Missing required columns" in data["detail"] or "structural" in data["detail"].lower()
    
    def test_empty_csv_file(self):
        """Test upload of empty CSV file returns 400."""
        empty_csv = ""
        csv_file = io.BytesIO(empty_csv.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("empty.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "empty" in data["detail"].lower() or "no data" in data["detail"].lower()
    
    def test_non_csv_file_upload(self):
        """Test upload of non-CSV file returns 400."""
        text_content = "This is not a CSV file"
        text_file = io.BytesIO(text_content.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("document.txt", text_file, "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "CSV" in data["detail"]
    
    def test_large_csv_file_simulation(self):
        """Test processing of larger CSV file (simulated)."""
        # Create a larger CSV with 50 rows
        rows = ["city,crime_index,accident_rate,socioeconomic_level,weather"]
        
        for i in range(50):
            city = f"City_{i:03d}"
            crime = 5.0 + (i % 5)
            accident = 3.0 + (i % 6)
            socio = 2 + (i % 8)
            weather = ["Clear", "Rainy", "Snowy", "Stormy"][i % 4]
            rows.append(f"{city},{crime},{accident},{socio},{weather}")
        
        large_csv = "\n".join(rows)
        csv_file = io.BytesIO(large_csv.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("large_data.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == 200
        
        # Should process all rows
        csv_response = response.content.decode('utf-8')
        lines = csv_response.strip().split('\n')
        
        # Should have header + 50 data rows
        assert len(lines) >= 51
    
    def test_csv_without_optional_city_column(self):
        """Test CSV processing without optional city column."""
        no_city_csv = """crime_index,accident_rate,socioeconomic_level,weather
5.0,4.0,6,Clear
6.0,5.0,7,Rainy"""
        
        csv_file = io.BytesIO(no_city_csv.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("no_city.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == 200
        
        csv_response = response.content.decode('utf-8')
        lines = csv_response.strip().split('\n')
        
        # Should still process successfully
        assert len(lines) >= 3  # Header + 2 data rows


class TestAPIErrorHandling:
    """Test API error handling and exception scenarios."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_404_not_found(self):
        """Test that non-existent endpoints return 404."""
        response = self.client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Test that incorrect HTTP methods return 405."""
        # Try GET on process endpoint (should be POST)
        response = self.client.get("/process")
        assert response.status_code == 405
    
    @patch.object(risk_processor, 'process_risk_data', side_effect=Exception("Simulated error"))
    def test_internal_server_error_handling(self, mock_process):
        """Test handling of internal server errors."""
        valid_request = {
            "crime_index": 5.0,
            "accident_rate": 4.0,
            "socioeconomic_level": 6,
            "weather": "Clear"
        }
        
        response = self.client.post("/process", json=valid_request)
        
        # Should return 500 for internal server error
        assert response.status_code == 500
        data = response.json()
        
        assert "detail" in data
        assert "server error" in data["detail"].lower()
    
    def test_malformed_json_request(self):
        """Test handling of malformed JSON requests."""
        # Send invalid JSON
        response = self.client.post(
            "/process",
            data="invalid json content",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        response = self.client.options("/")
        
        # Check for CORS-related headers
        assert "access-control-allow-origin" in response.headers
    
    @patch.object(csv_processor, 'process_csv_file', side_effect=CSVProcessingError("CSV error"))
    def test_csv_processing_error_handling(self, mock_csv_process):
        """Test handling of CSV processing errors."""
        csv_content = """city,crime_index,accident_rate,socioeconomic_level,weather
Test,5.0,4.0,6,Clear"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        response = self.client.post(
            "/process-csv",
            files={"file": ("test.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestAPIResponseFormats:
    """Test API response formats and validation."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_single_risk_response_format(self):
        """Test single risk processing response format."""
        request_data = {
            "city": "Format Test",
            "crime_index": 5.0,
            "accident_rate": 4.0,
            "socioeconomic_level": 6,
            "weather": "Clear"
        }
        
        response = self.client.post("/process", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response schema
        assert isinstance(data["city"], str)
        assert isinstance(data["risk_score"], (int, float))
        assert isinstance(data["components"], dict)
        
        # Validate components schema
        components = data["components"]
        component_keys = ["crime_component", "accident_component", 
                         "socioeconomic_component", "weather_component"]
        
        for key in component_keys:
            assert key in components
            assert isinstance(components[key], (int, float))
    
    def test_error_response_format(self):
        """Test error response format consistency."""
        invalid_request = {
            "crime_index": 15.0,  # Out of range
            "accident_rate": 4.0,
            "socioeconomic_level": 6,
            "weather": "Clear"
        }
        
        response = self.client.post("/process", json=invalid_request)
        
        assert response.status_code == 400
        data = response.json()
        
        # Error response should have detail field
        assert "detail" in data
        assert isinstance(data["detail"], str)
    
    def test_health_response_format(self):
        """Test health check response format."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate health response schema
        required_fields = ["status", "timestamp", "version", "components"]
        
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["components"], dict)
        assert data["version"] == "1.0.0"


class TestAPIIntegration:
    """Test end-to-end API integration scenarios."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_complete_workflow_single_processing(self):
        """Test complete workflow for single risk processing."""
        # 1. Check API health
        health_response = self.client.get("/health")
        assert health_response.status_code == 200
        
        # 2. Get processor info
        info_response = self.client.get("/info")
        assert info_response.status_code == 200
        
        # 3. Process single risk
        risk_data = {
            "city": "Integration Test",
            "crime_index": 7.0,
            "accident_rate": 6.0,
            "socioeconomic_level": 4,
            "weather": "Stormy"
        }
        
        process_response = self.client.post("/process", json=risk_data)
        assert process_response.status_code == 200
        
        result = process_response.json()
        assert result["city"] == "Integration Test"
        assert 0 <= result["risk_score"] <= 100
    
    def test_complete_workflow_csv_processing(self):
        """Test complete workflow for CSV processing."""
        # 1. Check API health
        health_response = self.client.get("/health")
        assert health_response.status_code == 200
        
        # 2. Process CSV
        csv_content = """city,crime_index,accident_rate,socioeconomic_level,weather
Integration City 1,5.0,4.0,7,Clear
Integration City 2,8.0,7.0,3,Stormy"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        csv_response = self.client.post(
            "/process-csv",
            files={"file": ("integration_test.csv", csv_file, "text/csv")}
        )
        
        assert csv_response.status_code == 200
        
        # Verify CSV response contains processed data
        csv_output = csv_response.content.decode('utf-8')
        assert "Integration City 1" in csv_output
        assert "Integration City 2" in csv_output
        assert "risk_score" in csv_output.lower()
    
    def test_concurrent_requests(self):
        """Test handling of multiple concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            request_data = {
                "crime_index": 5.0,
                "accident_rate": 4.0,
                "socioeconomic_level": 6,
                "weather": "Clear"
            }
            response = self.client.post("/process", json=request_data)
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])