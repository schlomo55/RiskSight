# Risk Processing API

A robust FastAPI-based service for transforming raw risk indicators into normalized risk scores with comprehensive error handling, multi-threaded CSV processing, and extensible configuration.

## Overview

The Risk Processing API evaluates risk based on four key indicators:
- **Crime Index** (0-10 scale): Local crime statistics
- **Accident Rate** (0-10 scale): Traffic/safety incident rates  
- **Socioeconomic Level** (1-10 scale): Economic stability indicators
- **Weather Conditions**: Categorical weather impact (Clear, Rainy, Snowy, Stormy, Extreme)

The system applies configurable weights, amplification rules, and statistical processing to generate normalized risk scores (0-100 scale) with detailed component breakdowns.

## Features

- ✅ **Multi-stage Risk Processing Pipeline** with configurable weights and rules
- ✅ **Extensible Amplification Rules** for risk interaction patterns
- ✅ **Dual Logging System** (general.log + error.log) with ISO-8601 timestamps
- ✅ **Multi-threaded CSV Processing** with per-row error tracking
- ✅ **Comprehensive Input Validation** with detailed error messages
- ✅ **RESTful API** with OpenAPI documentation
- ✅ **Docker Support** with Python 3.12 slim
- ✅ **Health Monitoring** and configuration endpoints
- ✅ **Statistical Noise Simulation** (configurable/deterministic modes)

## Quick Start

### Prerequisites

- Python 3.12+
- Docker (optional)
- 8GB RAM recommended for large CSV processing

### Installation & Setup

1. **Clone and Setup Environment**
   ```bash
   git clone https://github.com/your-organization/RiskSight.git
   cd RiskSight
   
   # Create virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   # Development server
   python main.py
   
   # Or with uvicorn directly
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Access the API**
   - **API Documentation**: http://localhost:8000/docs
   - **Alternative Docs**: http://localhost:8000/redoc
   - **Health Check**: http://localhost:8000/health
   - **API Root**: http://localhost:8000/

### Docker Deployment

```bash
# Build the image
docker build -t risk-processor-api .

# Run the container
docker run -p 8000:8000 -v $(pwd)/logs:/app/logs risk-processor-api

# Or with docker-compose (create docker-compose.yml as needed)
docker-compose up --build
```

## API Documentation

### Endpoints

#### POST `/process` - Single Risk Processing
Process individual risk data points with immediate response.

**Request Body:**
```json
{
  "city": "New York",
  "crime_index": 7.5,
  "accident_rate": 6.2,
  "socioeconomic_level": 4,
  "weather": "Rainy"
}
```

**Response:**
```json
{
  "city": "New York",
  "risk_score": 72.45,
  "components": {
    "crime_component": 75.0,
    "accident_component": 62.0,
    "socioeconomic_component": 60.0,
    "weather_component": 50.0
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "Unknown weather: Foggy"
}
```

#### POST `/process-csv` - Batch CSV Processing
Upload CSV files for concurrent processing with comprehensive error handling.

**CSV Format Requirements:**
- **Required Columns**: `crime_index`, `accident_rate`, `socioeconomic_level`, `weather`
- **Optional Columns**: `city`
- **File Size**: Max 100MB
- **Encoding**: UTF-8

**Sample CSV Input:**
```csv
city,crime_index,accident_rate,socioeconomic_level,weather
New York,7.5,6.2,4,Rainy
Los Angeles,5.8,8.1,6,Clear
Chicago,8.2,7.3,3,Stormy
```

**CSV Output** (includes all input columns plus):
- `risk_score`: Final aggregated score (0-100)
- `crime_component`: Crime risk component (0-100)  
- `accident_component`: Accident risk component (0-100)
- `socioeconomic_component`: Socioeconomic risk component (0-100)
- `weather_component`: Weather risk component (0-100)
- `processing_status`: SUCCESS or ERROR
- `error_message`: Detailed error description (if ERROR)

**Error Row Handling:**
- Rows with validation errors remain in output
- Score columns are left blank for error rows
- `processing_status=ERROR` with detailed `error_message`
- Batch processing never fails due to individual row errors

#### GET `/health` - Health Check
Returns system health status for monitoring.

```json
{
  "status": "healthy",
  "timestamp": "2023-09-08T14:46:00Z",
  "version": "1.0.0",
  "components": {
    "risk_processor": "healthy",
    "csv_processor": "healthy", 
    "logging": "healthy"
  }
}
```

#### GET `/info` - Configuration Information
Returns current processor configuration.

```json
{
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
```

## Configuration

All system behavior is controlled via `config/constants.py`:

### Risk Processing Configuration
```python
# Component weights (must sum to ~1.0)
DEFAULT_WEIGHTS = {
    "crime_index": 0.30,
    "accident_rate": 0.25, 
    "socioeconomic_level": 0.25,
    "weather": 0.20
}

# Weather risk mapping (0-1 scale)
WEATHER_CATEGORIES = {
    "Clear": 0.10,
    "Rainy": 0.50,
    "Snowy": 0.70,
    "Stormy": 0.90,
    "Extreme": 0.95,
}
```

### Extensible Amplification Rules
```python
DEFAULT_RULES = [
    {
        "conditions": {
            "crime_index": ">7", 
            "weather": {"Stormy", "Snowy"}
        }, 
        "multiplier": 1.15,
        "description": "High crime + severe weather amplification"
    },
    {
        "conditions": {
            "accident_rate": ">8", 
            "socioeconomic_level": "<3"
        }, 
        "multiplier": 1.10,
        "description": "High accidents + low socioeconomic amplification"
    }
    # Add new rules here without code changes
]
```

### Performance Settings
```python
CSV_MAX_WORKERS = 8        # Concurrent processing threads
DEFAULT_NOISE_LEVEL = 0.05 # Statistical noise (0.0 = deterministic)
MAX_UPLOAD_SIZE_MB = 100   # Maximum CSV file size
```

## Usage Examples

### Python Client Example
```python
import requests
import json

# Single risk processing
data = {
    "city": "San Francisco",
    "crime_index": 6.5,
    "accident_rate": 7.2, 
    "socioeconomic_level": 7,
    "weather": "Clear"
}

response = requests.post("http://localhost:8000/process", json=data)
result = response.json()
print(f"Risk Score: {result['risk_score']}")
print(f"Components: {result['components']}")
```

### cURL Examples
```bash
# Single risk processing
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Boston",
    "crime_index": 5.5,
    "accident_rate": 4.8,
    "socioeconomic_level": 8,
    "weather": "Snowy"
  }'

# CSV file upload  
curl -X POST "http://localhost:8000/process-csv" \
  -F "file=@sample_data.csv" \
  --output processed_sample_data.csv

# Health check
curl "http://localhost:8000/health"
```

## Architecture

The system follows clean architecture principles with clear separation of concerns:

```
├── config/           # Configuration and constants
├── core/            # Business logic
│   ├── models.py    # Pydantic data models
│   ├── validators.py # Input validation 
│   └── risk_processor.py # Main processing engine
├── services/        # Infrastructure services
│   ├── logger_service.py # Dual logging system
│   └── csv_processor.py  # Multi-threaded CSV processing
├── api/             # Web interface
│   ├── routes.py    # FastAPI endpoints
│   └── responses.py # Response models
├── logs/            # Log files (general.log, error.log)
├── docs/            # Documentation
└── tests/           # Test suite
```

## Logging

The system maintains two separate log files:

- **`logs/general.log`**: Informational messages, processing summaries
- **`logs/error.log`**: Errors, exceptions, validation failures

All logs use ISO-8601 timestamps and structured formatting:
```
2023-09-08T14:46:00 | INFO | Processing single risk request | city: Boston
2023-09-08T14:46:01 | ERROR | Row 25: Unknown weather: Foggy
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_risk_processor.py -v  # Core logic tests
python -m pytest tests/test_csv_processor.py -v   # CSV processing tests  
python -m pytest tests/test_api.py -v            # API integration tests

# Test with deterministic mode (no statistical noise)
python -m pytest tests/ -v --deterministic
```

## Error Handling

The system provides comprehensive error handling:

### JSON Endpoint Errors
- **400 Bad Request**: Validation errors (unknown weather, out-of-range values)
- **500 Internal Server Error**: Processing failures

### CSV Processing Errors
- **Structural Errors**: Missing columns, empty files → 400 Bad Request
- **Row-level Errors**: Invalid data → Row marked with `processing_status=ERROR`
- **Processing never fails** due to individual row errors

### Common Error Messages
- `Unknown weather: Foggy` - Invalid weather category
- `crime_index must be between 0 and 10` - Out of range value
- `Missing required field: weather` - Missing required data

## Performance Considerations

- **CSV Processing**: Up to 8 concurrent workers (configurable)
- **Memory Usage**: ~50MB base + ~1MB per 1000 CSV rows  
- **Processing Speed**: ~1000 rows/second on typical hardware
- **File Limits**: 100MB max upload size
- **Concurrent Requests**: Supports multiple simultaneous API calls

## Security Features

- **Input Validation**: Comprehensive validation with sanitization
- **Error Handling**: No sensitive data exposure in logs or responses  
- **Docker Security**: Non-root user execution
- **CORS**: Configurable cross-origin request handling
- **File Upload**: Size limits and type validation

## Monitoring & Health Checks

- **Health Endpoint**: `/health` for load balancer checks
- **Configuration Endpoint**: `/info` for system status
- **Log Monitoring**: Structured logging for external monitoring tools
- **Docker Health Check**: Built-in container health monitoring

## Troubleshooting

### Common Issues

1. **Port 8000 already in use**
   ```bash
   # Use different port
   uvicorn main:app --port 8001
   ```

2. **Permission errors with logs**
   ```bash
   # Ensure logs directory is writable
   chmod 755 logs/
   ```

3. **CSV processing slow**
   - Check CSV file size (<100MB recommended)
   - Increase worker count in `config/constants.py`
   - Ensure sufficient RAM availability

4. **Docker container fails to start**
   ```bash
   # Check container logs
   docker logs <container-id>
   
   # Verify port mapping
   docker run -p 8000:8000 risk-processor-api
   ```

## Contributing

We welcome contributions to the RiskSight project! Please follow these guidelines to ensure smooth collaboration.

### Development Workflow

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub, then:
   git clone https://github.com/your-username/RiskSight.git
   cd RiskSight
   git remote add upstream https://github.com/your-organization/RiskSight.git
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies including dev tools
   pip install -r requirements.txt
   pip install pytest black flake8  # Development tools
   ```

3. **Create Feature Branch**
   ```bash
   # Always branch from main
   git checkout main
   git pull upstream main
   git checkout -b feature/your-feature-name
   ```

### Git Workflow Guidelines

#### Branch Naming Convention
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

#### Commit Message Convention
Follow conventional commit format for clear history:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic changes)
- `refactor`: Code restructuring (no feature changes)
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(risk-processor): add weather amplification rules"
git commit -m "fix(csv-processor): handle empty rows correctly"
git commit -m "docs(readme): update API examples"
```

#### Development Process

1. **Before Coding**
   ```bash
   # Ensure you're on latest main
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main  # Resolve any conflicts
   ```

2. **During Development**
   ```bash
   # Make small, logical commits
   git add .
   git commit -m "feat(scope): descriptive message"
   
   # Run tests frequently
   python -m pytest tests/ -v
   ```

3. **Before Submitting**
   ```bash
   # Format code
   black src/ tests/
   
   # Run linting
   flake8 src/ tests/
   
   # Run full test suite
   python -m pytest tests/ -v
   
   # Update documentation if needed
   ```

4. **Submit Pull Request**
   ```bash
   # Push feature branch
   git push origin feature/your-feature-name
   
   # Create PR on GitHub with:
   # - Clear title and description
   # - Reference related issues
   # - Include testing details
   ```

### Code Quality Standards

1. **Follow existing code structure and naming conventions**
2. **Update `config/constants.py` for configuration changes**
3. **Add comprehensive tests for new functionality**
4. **Update documentation for API changes**
5. **Ensure all tests pass before submitting changes**
6. **Follow Python PEP 8 style guide**
7. **Add docstrings for all public methods and classes**
8. **Handle errors gracefully with proper logging**

### Testing Requirements

- Write unit tests for all new features
- Maintain test coverage above 80%
- Test both success and error scenarios
- Include integration tests for API endpoints
- Test CSV processing with various data formats

### Documentation Requirements

- Update README.md for user-facing changes
- Update API documentation in docstrings
- Add code comments for complex logic
- Update configuration documentation
- Include usage examples for new features

### Review Process

1. All changes require pull request review
2. Automated tests must pass
3. Code must be properly formatted
4. Documentation must be updated
5. At least one maintainer approval required

### Getting Help

- Check existing issues and discussions
- Review the architecture documentation
- Test your changes with the examples provided
- Ask questions in pull request discussions

## License

[Specify your license here]

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review logs in `logs/` directory
3. Test with the `/health` endpoint
4. Verify configuration with `/info` endpoint

---

**Risk Processing API v1.0.0** - Transforming raw risk indicators into actionable intelligence.