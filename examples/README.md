# Risk Processing API - Examples and Usage Guide

This directory contains comprehensive examples and sample data for the Risk Processing API, demonstrating various usage scenarios, error handling, and integration patterns.

## 📁 Contents Overview

| File | Description | Purpose |
|------|-------------|---------|
| `sample_valid_data.csv` | 50 realistic city risk assessments | Testing valid data processing |
| `sample_error_data.csv` | 25 rows with intentional errors | Testing error handling |
| `python_usage_examples.py` | Complete Python client with examples | Programmatic API integration |
| `curl_usage_examples.sh` | Bash script with cURL examples | Command-line API testing |
| `README.md` | This documentation file | Usage guide and reference |

## 🚀 Quick Start

### Prerequisites

1. **Start the API server:**
   ```bash
   # From the project root directory
   python main.py
   ```
   The API will be available at `http://localhost:8000`

2. **Verify API is running:**
   ```bash
   curl http://localhost:8000/health
   ```

### Running the Examples

#### Python Examples
```bash
# Install dependencies (if not already installed)
pip install requests

# Run all Python examples
cd examples
python python_usage_examples.py
```

#### cURL Examples (Linux/macOS/WSL)
```bash
# Make the script executable
chmod +x curl_usage_examples.sh

# Run all cURL examples
./curl_usage_examples.sh
```

#### Windows (PowerShell/CMD)
Use individual cURL commands from the script or run the Python examples instead.

## 📊 Sample Data Files

### `sample_valid_data.csv`
**Purpose**: Demonstrates successful processing with realistic data
- **Rows**: 50 major US cities
- **Data Range**: 
  - Crime Index: 2.8 - 9.3 (0-10 scale)
  - Accident Rate: 4.2 - 8.4 (0-10 scale) 
  - Socioeconomic Level: 2 - 9 (1-10 scale)
  - Weather: All 5 categories (Clear, Rainy, Snowy, Stormy, Extreme)

**Sample Rows**:
```csv
city,crime_index,accident_rate,socioeconomic_level,weather
New York City,7.8,6.5,5,Rainy
San Francisco,5.8,6.3,8,Clear
Detroit,9.1,8.2,2,Snowy
```

**Expected Results**: All 50 rows should process successfully with calculated risk scores and component breakdowns.

### `sample_error_data.csv` 
**Purpose**: Tests comprehensive error handling capabilities
- **Rows**: 25 rows (mix of valid and invalid data)
- **Error Types**:
  - Out of range values (crime_index: 15.0, accident_rate: 12.0)
  - Invalid weather categories ("Foggy", "Sunny", "clear")
  - Missing required fields (empty crime_index, missing weather)
  - Invalid data types ("high", "medium", "abc")
  - Boundary violations (socioeconomic_level: 0, 15)

**Sample Error Rows**:
```csv
city,crime_index,accident_rate,socioeconomic_level,weather
Out of Range Crime,15.0,5.0,6,Clear
Invalid Weather,5.0,4.0,6,Foggy
Missing Crime,,4.0,6,Clear
String Crime,high,4.0,6,Clear
```

**Expected Results**: 
- Valid rows (7 total): Processed successfully with risk scores
- Error rows (18 total): Marked with `processing_status=ERROR` and detailed error messages

## 🐍 Python Examples (`python_usage_examples.py`)

### Features
- **Complete API Client**: `RiskProcessingAPIClient` class with all endpoint methods
- **Error Handling**: Comprehensive exception handling and validation
- **7 Detailed Examples**: Covering all major use cases
- **Automatic Validation**: Checks API availability before running examples

### Examples Included

#### 1. Basic Single Risk Processing
```python
risk_data = {
    "city": "San Francisco",
    "crime_index": 5.8,
    "accident_rate": 6.3,
    "socioeconomic_level": 8,
    "weather": "Clear"
}
result = client.process_single_risk(risk_data)
```

#### 2. High Risk Scenario with Amplification
Demonstrates amplification rules:
- High crime (>7) + Severe weather → ×1.15 multiplier
- High accidents (>8) + Low socioeconomic (<3) → ×1.10 multiplier

#### 3. Validation Error Handling
Tests various validation scenarios:
- Invalid weather categories
- Out-of-range values
- Missing required fields

#### 4. CSV File Processing
Batch processing with statistics:
```python
result_csv = client.process_csv_file("sample_valid_data.csv")
# Automatically saves processed results
# Shows processing statistics
```

#### 5. CSV Error Handling
Demonstrates robust error processing:
- Error rows preserved in output
- Detailed error messages
- Processing statistics with error rates

#### 6. API Health and Configuration
System monitoring and configuration retrieval:
```python
health = client.health_check()
config = client.get_processor_info()
```

#### 7. Batch vs Individual Processing Comparison
Validates consistency between processing methods.

### Usage
```bash
cd examples
python python_usage_examples.py
```

### Output Files
- `processed_sample_data.csv`: Results from valid data processing
- `processed_error_data.csv`: Results from error data processing

## 📡 cURL Examples (`curl_usage_examples.sh`)

### Features
- **15 Comprehensive Examples**: All API endpoints and error scenarios
- **Colored Output**: Easy-to-read formatted results
- **HTTP Status Validation**: Checks expected response codes
- **Automatic File Generation**: Saves processed CSV results
- **Error Simulation**: Tests various failure scenarios

### Examples Included

1. **API Root Information** - Basic API metadata
2. **Health Check** - System status verification
3. **Processor Configuration** - Current settings and weights
4. **Basic Single Risk Processing** - Standard risk assessment
5. **High Risk Scenario** - Amplification rule testing
6. **Invalid Weather Validation** - 400 error testing
7. **Out of Range Values** - Range validation testing
8. **Missing Required Fields** - Field validation testing
9. **CSV Upload (Valid)** - Batch processing success
10. **CSV Upload (Errors)** - Error handling in batch
11. **Invalid CSV Structure** - Structural validation
12. **Non-CSV File Upload** - File type validation
13. **Boundary Value Testing** - Min/max value testing
14. **Method Not Allowed** - HTTP method validation
15. **404 Not Found** - Endpoint validation

### Key Commands

#### Single Risk Processing
```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{
       "city": "San Francisco",
       "crime_index": 5.8,
       "accident_rate": 6.3,
       "socioeconomic_level": 8,
       "weather": "Clear"
     }'
```

#### CSV File Upload
```bash
curl -X POST "http://localhost:8000/process-csv" \
     -F "file=@sample_valid_data.csv"
```

#### Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

### Output Files
- `processed_valid_data_curl.csv`: cURL processed valid data
- `processed_error_data_curl.csv`: cURL processed error data

## 🎯 Usage Scenarios

### For Developers
1. **API Integration Testing**: Use Python examples to understand client implementation
2. **Error Handling**: Study error scenarios and response formats
3. **Performance Testing**: Process larger CSV files to test throughput
4. **Configuration Validation**: Check system settings and rules

### For QA Testing
1. **Functional Testing**: Run all examples to verify API functionality
2. **Error Testing**: Use error data samples to validate error handling
3. **Boundary Testing**: Test min/max values and edge cases
4. **Integration Testing**: Verify end-to-end workflows

### for Operations
1. **Health Monitoring**: Use health check examples for monitoring setup
2. **Performance Monitoring**: Analyze CSV processing times
3. **Configuration Verification**: Check processor settings
4. **Troubleshooting**: Use examples to diagnose issues

## 📈 Expected Results

### Successful Processing
```json
{
  "city": "San Francisco",
  "risk_score": 45.23,
  "components": {
    "crime_component": 58.0,
    "accident_component": 63.0,
    "socioeconomic_component": 22.22,
    "weather_component": 10.0
  }
}
```

### Error Handling
```json
{
  "detail": "Unknown weather: Foggy"
}
```

### CSV Processing Statistics
```
Total rows: 50
Successful rows: 50
Error rows: 0
Processing time: 2.45 seconds
```

## 🔧 Customization

### Modifying Sample Data
1. **Add New Cities**: Extend `sample_valid_data.csv` with additional records
2. **Create Error Scenarios**: Add specific error cases to `sample_error_data.csv`
3. **Test Edge Cases**: Create boundary condition tests

### Extending Examples
1. **Add New Scenarios**: Extend Python examples with additional use cases
2. **Performance Testing**: Create larger datasets for load testing
3. **Integration Testing**: Add multi-step workflow examples

### Configuration Testing
1. **Different Weights**: Test with modified risk component weights
2. **New Rules**: Test additional amplification rules
3. **Weather Categories**: Test with extended weather conditions

## 🚨 Troubleshooting

### Common Issues

#### API Not Available
```
❌ Cannot connect to API at http://localhost:8000
```
**Solution**: Start the API server with `python main.py`

#### File Not Found Errors
```
Error: File not found: sample_valid_data.csv
```
**Solution**: Run examples from the `examples/` directory

#### Permission Errors (Linux/macOS)
```
Permission denied: ./curl_usage_examples.sh
```
**Solution**: Make script executable with `chmod +x curl_usage_examples.sh`

#### Python Import Errors
```
ModuleNotFoundError: No module named 'requests'
```
**Solution**: Install dependencies with `pip install requests`

### Validation Failures

#### Unexpected Status Codes
- Check API server is running
- Verify endpoint URLs are correct
- Confirm request format matches API requirements

#### Processing Errors
- Validate CSV file format and encoding (UTF-8)
- Check column names match requirements
- Verify data types and ranges

## 📚 Additional Resources

### API Documentation
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

### Configuration Reference
- **Risk Weights**: See `config/constants.py` for component weights
- **Weather Categories**: Clear, Rainy, Snowy, Stormy, Extreme
- **Input Ranges**: 
  - Crime Index: 0-10
  - Accident Rate: 0-10
  - Socioeconomic Level: 1-10

### Related Documentation
- **System Architecture**: `../docs/architecture.md`
- **How It Works**: `../docs/how_it_works.md`  
- **Task List**: `../docs/task_list.md`
- **Main README**: `../README.md`

---

## 🎉 Getting Started Checklist

- [ ] Start the API server (`python main.py`)
- [ ] Verify API health (`curl http://localhost:8000/health`)
- [ ] Run Python examples (`python python_usage_examples.py`)
- [ ] Try cURL examples (`./curl_usage_examples.sh` or individual commands)
- [ ] Upload your own CSV data for processing
- [ ] Explore the interactive API documentation at `/docs`

**Happy risk processing! 🎯**