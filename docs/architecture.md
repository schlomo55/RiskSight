# Risk Processing API - System Architecture

## Overview

The Risk Processing API is designed following **Clean Architecture** principles with clear separation of concerns, dependency inversion, and extensible design patterns. The system transforms raw risk indicators into normalized risk scores through a multi-stage processing pipeline.

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Layer    │    │  Services Layer │    │   Core Layer    │
│                │    │                 │    │                 │
│ • FastAPI      │───▶│ • LoggerService │───▶│ • RiskProcessor │
│ • Routes       │    │ • CSVProcessor  │    │ • Validators    │
│ • Responses    │    │ • Threading     │    │ • Models        │
│                │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Configuration   │
                    │                 │
                    │ • Constants     │
                    │ • Rules         │
                    │ • Settings      │
                    │                 │
                    └─────────────────┘
```

## Component Architecture

### 1. Configuration Layer (`config/`)

**Purpose**: Centralized configuration management  
**Pattern**: Configuration as Code

```python
# config/constants.py - Single source of truth
DEFAULT_WEIGHTS = {...}           # Component weights
WEATHER_CATEGORIES = {...}        # Weather risk mapping
DEFAULT_RULES = [...]            # Amplification rules
CSV_MAX_WORKERS = 8              # Performance settings
LOG_PATHS = {...}                # System configuration
```

**Design Principles**:
- All tunables centralized in one file
- No magic numbers in code
- Easy modification without code changes
- Environment-specific overrides supported

### 2. Core Business Logic (`core/`)

**Purpose**: Domain logic and business rules  
**Pattern**: Domain-Driven Design

#### 2.1 Data Models (`core/models.py`)
```
RiskDataInput
├── Validation: Pydantic validators
├── Field constraints: Range validation
└── Weather category validation

RiskProcessingResult
├── Component breakdown
├── Final aggregated score
└── Optional metadata

Error Models
├── ProcessingError
├── ValidationErrorDetails
└── CSVProcessingSummary
```

#### 2.2 Risk Processor (`core/risk_processor.py`)
```
RiskProcessor
├── __init__(weights, rules, noise_level)
├── process_risk_data() → Dict
├── _calculate_component_scores() → Dict
├── _apply_amplification_rules() → float
├── _add_statistical_noise() → float
└── set_deterministic_mode() → void

Multi-Stage Pipeline:
1. Input validation
2. Component normalization
3. Weighted aggregation
4. Rule amplification
5. Statistical noise
6. Output scaling
```

#### 2.3 Validators (`core/validators.py`)
```
RiskDataValidator
├── validate_risk_data() → Dict
├── _validate_crime_index() → float
├── _validate_accident_rate() → float
├── _validate_socioeconomic_level() → float
└── _validate_weather() → str

CSVValidator
├── validate_csv_structure() → List[str]
├── validate_csv_row() → Dict
└── get_validation_summary() → Dict
```

### 3. Services Layer (`services/`)

**Purpose**: Infrastructure and cross-cutting concerns  
**Pattern**: Service Layer Pattern

#### 3.1 Logger Service (`services/logger_service.py`)
```
LoggerService (Singleton)
├── Dual file logging (general.log + error.log)
├── ISO-8601 timestamps
├── Structured formatting
├── Sensitive data sanitization
└── Context-aware logging methods

Methods:
├── log_info(message, context)
├── log_error(message, error, context)
├── log_validation_error(field, value, message)
└── log_csv_processing_summary(stats)
```

#### 3.2 CSV Processor (`services/csv_processor.py`)
```
CSVProcessor
├── Multi-threaded processing (ThreadPoolExecutor)
├── Per-row error handling
├── Result DataFrame management
└── Processing statistics

Processing Flow:
1. Parse CSV content
2. Validate structure
3. Submit rows to thread pool
4. Collect results with error tracking
5. Generate output DataFrame
6. Log processing summary
```

### 4. API Layer (`api/`)

**Purpose**: HTTP interface and request/response handling  
**Pattern**: Controller Pattern

#### 4.1 FastAPI Routes (`api/routes.py`)
```
Endpoints:
├── POST /process - Single risk processing
├── POST /process-csv - Batch CSV processing
├── GET /health - Health check
├── GET /info - Configuration info
└── GET / - API root information

Error Handling:
├── ValidationError → 400 Bad Request
├── CSVProcessingError → 400 Bad Request
├── Processing failures → 500 Internal Server Error
└── Custom exception handlers
```

#### 4.2 Response Models (`api/responses.py`)
```
Response Models:
├── RiskProcessingResponse
├── RiskComponentsResponse
├── ErrorResponse
├── HealthCheckResponse
├── ProcessorInfoResponse
└── DetailedErrorResponse
```

## Data Flow Architecture

### Single Risk Processing Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ HTTP Request│───▶│ FastAPI      │───▶│ RiskProcessor   │
│ (JSON)      │    │ Validation   │    │ Multi-stage     │
└─────────────┘    └──────────────┘    │ Pipeline        │
                                       └─────────────────┘
                                                │
┌─────────────┐    ┌──────────────┐           ▼
│ HTTP Response◀───│ Response     │    ┌─────────────────┐
│ (JSON)      │    │ Formatting   │◀───│ Risk Score +    │
└─────────────┘    └──────────────┘    │ Components      │
                                       └─────────────────┘
```

### CSV Processing Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ CSV Upload  │───▶│ File         │───▶│ Structure       │
│             │    │ Validation   │    │ Validation      │
└─────────────┘    └──────────────┘    └─────────────────┘
                                                │
                                               ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Processed   │◀───│ Result       │◀───│ ThreadPool      │
│ CSV Download│    │ Aggregation  │    │ Processing      │
└─────────────┘    └──────────────┘    └─────────────────┘
                                                │
                                               ▼
                                    ┌─────────────────┐
                                    │ Per-row         │
                                    │ Risk Processing │
                                    │ + Error Tracking│
                                    └─────────────────┘
```

## Risk Processing Pipeline

### Stage 1: Input Validation
```
Raw Input → Validation → Clean Data
├── Type checking (int/float/str)
├── Range validation (0-10, 1-10)
├── Weather category validation
└── Required field presence
```

### Stage 2: Component Normalization
```
Clean Data → Normalization → Component Scores (0-1)
├── Crime Index: value / 10.0
├── Accident Rate: value / 10.0
├── Socioeconomic: (11 - value) / 9.0  [inverted]
└── Weather: lookup from mapping
```

### Stage 3: Weighted Aggregation
```
Component Scores → Weights → Base Score
Base Score = Σ(component_score × weight)
Default Weights:
├── Crime Index: 30%
├── Accident Rate: 25%
├── Socioeconomic: 25%
└── Weather: 20%
```

### Stage 4: Rule Amplification
```
Base Score + Rules → Amplified Score
Rule Evaluation:
├── Condition matching (">7", "<3", set membership)
├── Cumulative multiplier application
├── Rule logging for transparency
└── Configurable rule set
```

### Stage 5: Statistical Noise
```
Amplified Score + Noise → Noisy Score
├── Uniform random distribution (±noise_level)
├── Deterministic mode (noise_level = 0.0)
├── Bounded to [0, 1] range
└── Configurable noise level
```

### Stage 6: Output Scaling
```
Noisy Score → Scaling → Final Score (0-100)
├── Scale to output range
├── Component score scaling
├── Result formatting
└── Response preparation
```

## Extensibility Design

### Adding New Weather Categories
```python
# config/constants.py
WEATHER_CATEGORIES = {
    "Clear": 0.10,
    "Rainy": 0.50,
    "Foggy": 0.40,     # New category
    "Snowy": 0.70,
    "Stormy": 0.90,
    "Extreme": 0.95,
}
```

### Adding New Amplification Rules
```python
# config/constants.py
DEFAULT_RULES = [
    # Existing rules...
    {
        "conditions": {
            "socioeconomic_level": "<2",
            "weather": {"Extreme"}
        },
        "multiplier": 1.25,
        "description": "Very low socioeconomic + extreme weather"
    }
]
```

### Adding New Risk Indicators
1. Update `RiskDataInput` model in `core/models.py`
2. Add validation logic in `core/validators.py`
3. Update component calculation in `risk_processor.py`
4. Adjust weights in `config/constants.py`
5. Update CSV output columns

## Error Handling Architecture

### Validation Error Flow
```
Invalid Input → Validator → ValidationError → HTTP 400
├── Field-level validation
├── Cross-field validation
├── Error message formatting
└── Client-friendly responses
```

### CSV Error Handling
```
Row Processing Error → Error Tracking → Result Row
├── Individual row failure isolation
├── Error row preservation in output
├── Detailed error messaging
└── Batch processing continuation
```

## Performance Architecture

### Threading Model
```
CSV Processing:
├── Main Thread: Coordination & I/O
├── Worker Threads: Risk processing (8 workers)
├── ThreadPoolExecutor management
└── Result collection & aggregation
```

### Memory Management
```
Memory Usage:
├── Base Application: ~50MB
├── Per-row Processing: ~1KB
├── CSV Buffer: File size dependent
└── Thread Pool: Worker thread overhead
```

## Security Architecture

### Input Validation
```
Security Layers:
├── Pydantic model validation
├── Custom validator logic
├── Type coercion protection
└── SQL injection prevention (N/A - no DB)
```

### Data Sanitization
```
Logging Security:
├── Sensitive field detection
├── Value length limitations
├── Data type sanitization
└── Context information filtering
```

### Docker Security
```
Container Security:
├── Non-root user execution
├── Minimal base image (slim)
├── Limited system dependencies
└── Health check integration
```

## Monitoring Architecture

### Health Check System
```
Health Monitoring:
├── Component status validation
├── Log file accessibility
├── System resource checks
└── Service availability confirmation
```

### Logging Architecture
```
Dual Logging System:
├── General Log: Info, debug, processing stats
├── Error Log: Errors, exceptions, stack traces
├── ISO-8601 timestamps
├── Structured formatting
└── Log rotation capability
```

## Deployment Architecture

### Development Deployment
```
Development Stack:
├── Python 3.12 virtual environment
├── FastAPI development server
├── Hot reload capability
└── Direct Python execution
```

### Production Deployment
```
Production Stack:
├── Docker containerization
├── Uvicorn ASGI server
├── Health check integration
├── Log volume mounting
└── Port mapping (8000)
```

## Design Patterns Used

1. **Singleton Pattern**: LoggerService for consistent logging
2. **Factory Pattern**: Processor initialization with configuration
3. **Strategy Pattern**: Extensible rule evaluation system
4. **Template Method**: Multi-stage processing pipeline
5. **Observer Pattern**: Event logging throughout pipeline
6. **Dependency Injection**: Service layer dependencies
7. **Configuration Pattern**: Centralized configuration management

## Quality Attributes

### Maintainability
- Clear separation of concerns
- Centralized configuration
- Comprehensive documentation
- Consistent coding patterns

### Extensibility  
- Plugin-like rule system
- Configurable processing parameters
- Modular component design
- Interface-based abstractions

### Reliability
- Comprehensive error handling
- Input validation at multiple layers
- Graceful failure modes
- Detailed logging and monitoring

### Performance
- Multi-threaded CSV processing
- Efficient data structures
- Minimal memory allocations
- Configurable worker pools

### Security
- Input sanitization
- No sensitive data exposure
- Container security practices
- Validation at API boundaries

---

This architecture provides a solid foundation for the Risk Processing API while maintaining flexibility for future enhancements and modifications.