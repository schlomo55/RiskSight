"""
Python Usage Examples for the Risk Processing API.

This module demonstrates how to interact with the Risk Processing API
using Python's requests library for various scenarios.
"""

import requests
import json
import csv
import os
from typing import Dict, List, Any

# API Configuration
API_BASE_URL = "http://localhost:8000"


class RiskProcessingAPIClient:
    """
    Python client for the Risk Processing API.
    
    Provides convenient methods for interacting with all API endpoints
    with proper error handling and response processing.
    """
    
    def __init__(self, base_url: str = API_BASE_URL):
        """Initialize the API client with base URL."""
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check API health status.
        
        Returns:
            Dictionary with health status information
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get processor configuration information.
        
        Returns:
            Dictionary with processor configuration details
        """
        try:
            response = self.session.get(f"{self.base_url}/info")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to get processor info: {e}")
            return {}
    
    def process_single_risk(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single risk assessment.
        
        Args:
            risk_data: Dictionary containing risk indicators
            
        Returns:
            Dictionary with risk score and component breakdown
        """
        try:
            response = self.session.post(
                f"{self.base_url}/process",
                json=risk_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                error_detail = response.json().get('detail', 'Validation error')
                print(f"Validation error: {error_detail}")
                return {"error": error_detail, "status_code": 400}
            else:
                print(f"HTTP error: {e}")
                return {"error": str(e), "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return {"error": str(e)}
    
    def process_csv_file(self, file_path: str) -> str:
        """
        Process a CSV file and return the processed CSV content.
        
        Args:
            file_path: Path to the CSV file to process
            
        Returns:
            Processed CSV content as string
        """
        try:
            with open(file_path, 'rb') as file:
                files = {'file': (os.path.basename(file_path), file, 'text/csv')}
                
                # Remove JSON content type for file upload
                headers = {k: v for k, v in self.session.headers.items() 
                          if k.lower() != 'content-type'}
                
                response = requests.post(
                    f"{self.base_url}/process-csv",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                
                return response.text
                
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                error_detail = response.json().get('detail', 'CSV processing error')
                print(f"CSV processing error: {error_detail}")
                return f"Error: {error_detail}"
            else:
                print(f"HTTP error: {e}")
                return f"Error: {e}"
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return f"Error: {e}"
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return f"Error: File not found: {file_path}"


# Example Usage Functions

def example_1_basic_single_risk_processing():
    """Example 1: Basic single risk processing."""
    print("=== Example 1: Basic Single Risk Processing ===")
    
    client = RiskProcessingAPIClient()
    
    # Sample risk data
    risk_data = {
        "city": "San Francisco",
        "crime_index": 5.8,
        "accident_rate": 6.3,
        "socioeconomic_level": 8,
        "weather": "Clear"
    }
    
    print("Processing risk data:")
    print(json.dumps(risk_data, indent=2))
    
    result = client.process_single_risk(risk_data)
    
    if "error" not in result:
        print("\nRisk Assessment Result:")
        print(f"City: {result['city']}")
        print(f"Overall Risk Score: {result['risk_score']}/100")
        print("\nComponent Breakdown:")
        components = result['components']
        for component, score in components.items():
            component_name = component.replace('_', ' ').title()
            print(f"  {component_name}: {score}/100")
    else:
        print(f"\nError: {result['error']}")
    
    print("-" * 50)


def example_2_high_risk_scenario():
    """Example 2: High risk scenario with amplification."""
    print("=== Example 2: High Risk Scenario ===")
    
    client = RiskProcessingAPIClient()
    
    # High risk data that should trigger amplification rules
    high_risk_data = {
        "city": "Detroit",
        "crime_index": 9.1,  # High crime (>7)
        "accident_rate": 8.2,
        "socioeconomic_level": 2,  # Low socioeconomic (<3)
        "weather": "Stormy"  # Severe weather
    }
    
    print("Processing high-risk scenario:")
    print(json.dumps(high_risk_data, indent=2))
    
    result = client.process_single_risk(high_risk_data)
    
    if "error" not in result:
        print(f"\nHigh Risk Assessment Result:")
        print(f"City: {result['city']}")
        print(f"Overall Risk Score: {result['risk_score']}/100")
        print("\nThis scenario should trigger amplification rules:")
        print("- High crime (>7) + Severe weather → ×1.15 multiplier")
        print("- High accidents (>8) + Low socioeconomic (<3) → ×1.10 multiplier")
    else:
        print(f"\nError: {result['error']}")
    
    print("-" * 50)


def example_3_validation_errors():
    """Example 3: Handling validation errors."""
    print("=== Example 3: Validation Error Handling ===")
    
    client = RiskProcessingAPIClient()
    
    # Invalid data that should cause validation errors
    invalid_scenarios = [
        {
            "name": "Invalid Weather Category",
            "data": {
                "city": "Test City",
                "crime_index": 5.0,
                "accident_rate": 4.0,
                "socioeconomic_level": 6,
                "weather": "Foggy"  # Invalid weather
            }
        },
        {
            "name": "Out of Range Crime Index",
            "data": {
                "city": "Test City",
                "crime_index": 15.0,  # Above maximum of 10
                "accident_rate": 4.0,
                "socioeconomic_level": 6,
                "weather": "Clear"
            }
        },
        {
            "name": "Missing Required Field",
            "data": {
                "city": "Test City",
                "crime_index": 5.0,
                "accident_rate": 4.0,
                # Missing socioeconomic_level and weather
            }
        }
    ]
    
    for scenario in invalid_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print(f"Data: {json.dumps(scenario['data'], indent=2)}")
        
        result = client.process_single_risk(scenario['data'])
        
        if "error" in result:
            print(f"Expected validation error: {result['error']}")
        else:
            print("Unexpected: No error occurred")
    
    print("-" * 50)


def example_4_csv_processing():
    """Example 4: CSV file processing."""
    print("=== Example 4: CSV File Processing ===")
    
    client = RiskProcessingAPIClient()
    
    # Process the sample valid data CSV
    csv_file_path = "sample_valid_data.csv"
    
    if os.path.exists(csv_file_path):
        print(f"Processing CSV file: {csv_file_path}")
        
        result_csv = client.process_csv_file(csv_file_path)
        
        if not result_csv.startswith("Error:"):
            # Save processed results
            output_file = "processed_sample_data.csv"
            with open(output_file, 'w', newline='') as f:
                f.write(result_csv)
            
            print(f"Processed CSV saved as: {output_file}")
            
            # Show some statistics
            lines = result_csv.strip().split('\n')
            total_rows = len(lines) - 1  # Exclude header
            
            print(f"Total rows processed: {total_rows}")
            
            # Count success/error rows
            success_count = result_csv.count('SUCCESS')
            error_count = result_csv.count('ERROR')
            
            print(f"Successful rows: {success_count}")
            print(f"Error rows: {error_count}")
            
        else:
            print(f"CSV processing failed: {result_csv}")
    else:
        print(f"CSV file not found: {csv_file_path}")
    
    print("-" * 50)


def example_5_csv_with_errors():
    """Example 5: CSV processing with error handling."""
    print("=== Example 5: CSV Processing with Errors ===")
    
    client = RiskProcessingAPIClient()
    
    # Process the sample error data CSV
    csv_file_path = "sample_error_data.csv"
    
    if os.path.exists(csv_file_path):
        print(f"Processing CSV with errors: {csv_file_path}")
        
        result_csv = client.process_csv_file(csv_file_path)
        
        if not result_csv.startswith("Error:"):
            # Save processed results
            output_file = "processed_error_data.csv"
            with open(output_file, 'w', newline='') as f:
                f.write(result_csv)
            
            print(f"Processed CSV saved as: {output_file}")
            
            # Analyze error handling
            lines = result_csv.strip().split('\n')
            total_rows = len(lines) - 1
            
            success_count = result_csv.count('SUCCESS')
            error_count = result_csv.count('ERROR')
            
            print(f"Total rows: {total_rows}")
            print(f"Successfully processed: {success_count}")
            print(f"Rows with errors: {error_count}")
            print(f"Error rate: {(error_count/total_rows)*100:.1f}%")
            
            # Show some error examples
            print("\nSample error messages:")
            for i, line in enumerate(lines[1:6]):  # Show first 5 data rows
                if 'ERROR' in line:
                    parts = line.split(',')
                    city = parts[0] if len(parts) > 0 else "Unknown"
                    error_msg = parts[-1] if len(parts) > 10 else "Unknown error"
                    print(f"  {city}: {error_msg}")
                    
        else:
            print(f"CSV processing failed: {result_csv}")
    else:
        print(f"CSV file not found: {csv_file_path}")
    
    print("-" * 50)


def example_6_api_health_and_info():
    """Example 6: API health check and configuration info."""
    print("=== Example 6: API Health Check and Configuration ===")
    
    client = RiskProcessingAPIClient()
    
    # Health check
    print("Checking API health...")
    health = client.health_check()
    
    if health.get("status") == "healthy":
        print("✅ API is healthy")
        print(f"Version: {health.get('version')}")
        print(f"Timestamp: {health.get('timestamp')}")
        
        components = health.get('components', {})
        print("Component status:")
        for component, status in components.items():
            status_icon = "✅" if status == "healthy" else "⚠️"
            print(f"  {status_icon} {component}: {status}")
    else:
        print("❌ API health check failed")
        print(f"Status: {health.get('status')}")
    
    # Get processor configuration
    print("\nGetting processor configuration...")
    config = client.get_processor_info()
    
    if config:
        print("Current configuration:")
        print(f"Output scale: {config.get('output_scale')}")
        print(f"Noise level: {config.get('noise_level')}")
        print(f"Active rules: {config.get('rules_count')}")
        print(f"CSV workers: {config.get('csv_max_workers')}")
        
        print("Component weights:")
        weights = config.get('weights', {})
        for component, weight in weights.items():
            print(f"  {component}: {weight*100:.0f}%")
        
        print("Weather categories:")
        categories = config.get('weather_categories', [])
        print(f"  {', '.join(categories)}")
    else:
        print("Failed to get processor configuration")
    
    print("-" * 50)


def example_7_batch_processing_comparison():
    """Example 7: Compare individual vs batch processing."""
    print("=== Example 7: Individual vs Batch Processing Comparison ===")
    
    client = RiskProcessingAPIClient()
    
    # Sample cities for comparison
    sample_cities = [
        {"city": "New York", "crime_index": 7.8, "accident_rate": 6.5, "socioeconomic_level": 5, "weather": "Rainy"},
        {"city": "San Francisco", "crime_index": 5.8, "accident_rate": 6.3, "socioeconomic_level": 8, "weather": "Clear"},
        {"city": "Detroit", "crime_index": 9.1, "accident_rate": 8.2, "socioeconomic_level": 2, "weather": "Snowy"}
    ]
    
    print("Processing cities individually:")
    individual_results = []
    
    for city_data in sample_cities:
        result = client.process_single_risk(city_data)
        if "error" not in result:
            individual_results.append({
                "city": result["city"],
                "risk_score": result["risk_score"],
                "components": result["components"]
            })
            print(f"  {result['city']}: {result['risk_score']:.1f}/100")
    
    # Create a temporary CSV for batch processing
    temp_csv = "temp_comparison.csv"
    with open(temp_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['city', 'crime_index', 'accident_rate', 'socioeconomic_level', 'weather'])
        writer.writeheader()
        writer.writerows(sample_cities)
    
    print(f"\nProcessing same cities via CSV batch:")
    batch_result = client.process_csv_file(temp_csv)
    
    if not batch_result.startswith("Error:"):
        lines = batch_result.strip().split('\n')
        header = lines[0].split(',')
        
        risk_score_idx = header.index('risk_score') if 'risk_score' in header else -1
        city_idx = header.index('city') if 'city' in header else 0
        
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) > risk_score_idx and risk_score_idx != -1:
                city = parts[city_idx]
                risk_score = parts[risk_score_idx]
                if risk_score and risk_score != '':
                    print(f"  {city}: {risk_score}/100")
    
    # Clean up temporary file
    if os.path.exists(temp_csv):
        os.remove(temp_csv)
    
    print("Both methods should produce identical results!")
    print("-" * 50)


def main():
    """Run all usage examples."""
    print("Risk Processing API - Python Usage Examples")
    print("=" * 60)
    
    # Check if API is available
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ API not available at {API_BASE_URL}")
            print("Please start the API server first:")
            print("  python main.py")
            return
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print("Please start the API server first:")
        print("  python main.py")
        return
    
    print(f"✅ API is available at {API_BASE_URL}")
    print()
    
    # Run examples
    example_1_basic_single_risk_processing()
    example_2_high_risk_scenario()
    example_3_validation_errors()
    example_4_csv_processing()
    example_5_csv_with_errors()
    example_6_api_health_and_info()
    example_7_batch_processing_comparison()
    
    print("All examples completed!")


if __name__ == "__main__":
    main()