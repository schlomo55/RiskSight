"""
FastAPI routes for the Risk Processing API.

Defines all API endpoints with comprehensive error handling,
validation, and proper response formatting. Includes both
JSON and CSV processing endpoints with detailed logging.
"""

import io
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError
import pandas as pd

from src.core.models import RiskDataInput
from src.core.risk_processor import RiskProcessor
from src.core.validators import ValidationError
from src.services.csv_processor import CSVProcessor, CSVProcessingError
from src.services.logger_service import LoggerService
from src.api.responses import (
    RiskProcessingResponse, RiskComponentsResponse, ErrorResponse,
    HealthCheckResponse, ProcessorInfoResponse
)
from src.config.constants import (
    API_TITLE, API_VERSION, API_DESCRIPTION, CSV_REQUIRED_COLUMNS,
    MAX_UPLOAD_SIZE_MB, WEATHER_CATEGORIES
)


# Initialize FastAPI application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
risk_processor = RiskProcessor()
csv_processor = CSVProcessor(risk_processor)
logger = LoggerService()

# Log application startup
logger.log_info("Risk Processing API starting up", {
    "version": API_VERSION,
    "title": API_TITLE
})


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.log_info("API startup complete", {
        "processor_config": risk_processor.get_processor_info(),
        "csv_max_workers": csv_processor.max_workers
    })


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown."""
    logger.log_info("API shutting down")


@app.post(
    "/process",
    response_model=RiskProcessingResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Process single risk data",
    description="""
    Process a single set of risk indicators and return the calculated risk score
    with component breakdown. Validates all input fields and returns detailed
    error messages for any validation failures.
    
    Returns 400 Bad Request for validation errors like unknown weather categories
    or out-of-range values.
    """
)
async def process_single_risk(request: RiskDataInput) -> RiskProcessingResponse:
    """
    Process single risk data point via JSON.
    
    Args:
        request: Risk data input with all required fields
        
    Returns:
        Structured response with risk score and component breakdown
        
    Raises:
        HTTPException: 400 for validation errors, 500 for processing errors
    """
    try:
        logger.log_info("Processing single risk request", {
            "city": request.city,
            "has_weather": bool(request.weather)
        })
        
        # Convert Pydantic model to dictionary for processing
        request_data = request.dict()
        
        # Process the risk data
        result = risk_processor.process_risk_data(request_data)
        
        # Create response model
        components = RiskComponentsResponse(
            crime_component=result["crime_index_component"],
            accident_component=result["accident_rate_component"],
            socioeconomic_component=result["socioeconomic_level_component"],
            weather_component=result["weather_component"]
        )
        
        response = RiskProcessingResponse(
            city=result.get("city"),
            risk_score=result["risk_score"],
            components=components
        )
        
        logger.log_info("Single risk processing completed", {
            "city": request.city,
            "risk_score": result["risk_score"]
        })
        
        return response
        
    except ValidationError as e:
        # Handle validation errors with 400 Bad Request
        error_message = str(e)
        logger.log_error(f"Validation error in single risk processing: {error_message}")
        
        # Extract field name if possible for better error reporting
        field_name = None
        if "weather" in error_message.lower():
            field_name = "weather"
        elif "crime" in error_message.lower():
            field_name = "crime_index"
        elif "accident" in error_message.lower():
            field_name = "accident_rate"
        elif "socio" in error_message.lower():
            field_name = "socioeconomic_level"
        
        raise HTTPException(
            status_code=400,
            detail=error_message
        )
        
    except ValueError as e:
        # Handle processing errors
        error_message = str(e)
        logger.log_error(f"Processing error in single risk processing: {error_message}")
        raise HTTPException(
            status_code=500,
            detail="Risk processing failed"
        )
        
    except Exception as e:
        # Handle unexpected errors
        error_message = f"Unexpected error: {str(e)}"
        logger.log_error("Unexpected error in single risk processing", e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.post(
    "/process-csv",
    responses={
        200: {"description": "Processed CSV file", "content": {"text/csv": {}}},
        400: {"model": ErrorResponse, "description": "CSV validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Process CSV file upload",
    description="""
    Process a CSV file containing multiple risk data records with concurrent processing.
    
    The CSV must contain the required columns: crime_index, accident_rate, 
    socioeconomic_level, weather. Optional columns like 'city' are supported.
    
    Error rows are retained in the output with processing_status=ERROR and 
    detailed error messages. The batch never fails due to individual row errors.
    
    Returns the processed CSV file with additional columns for risk scores,
    component breakdowns, and error tracking.
    """
)
async def process_csv_upload(file: UploadFile = File(...)) -> StreamingResponse:
    """
    Process CSV file upload with concurrent processing.
    
    Args:
        file: Uploaded CSV file
        
    Returns:
        StreamingResponse with processed CSV content
        
    Raises:
        HTTPException: 400 for file/structure errors, 500 for processing errors
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.csv'):
            logger.log_error(f"Invalid file type uploaded: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="File must be a CSV file"
            )
        
        # Check file size (rough estimate)
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        if file_size_mb > MAX_UPLOAD_SIZE_MB:
            logger.log_error(f"File too large: {file_size_mb:.2f}MB")
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {MAX_UPLOAD_SIZE_MB}MB limit"
            )
        
        # Decode file content
        try:
            content_str = file_content.decode('utf-8')
        except UnicodeDecodeError:
            logger.log_error(f"Failed to decode CSV file: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="CSV file must be UTF-8 encoded"
            )
        
        logger.log_info("Starting CSV processing", {
            "filename": file.filename,
            "size_mb": round(file_size_mb, 2)
        })
        
        # Process CSV with the CSV processor
        result_df = csv_processor.process_csv_file(content_str, file.filename)
        
        # Convert result to CSV string
        output_buffer = io.StringIO()
        result_df.to_csv(output_buffer, index=False)
        output_buffer.seek(0)
        csv_content = output_buffer.getvalue()
        
        # Create filename for download
        original_name = file.filename.rsplit('.', 1)[0] if '.' in file.filename else file.filename
        download_filename = f"processed_{original_name}.csv"
        
        logger.log_info("CSV processing completed successfully", {
            "filename": file.filename,
            "output_filename": download_filename,
            "total_rows": len(result_df)
        })
        
        # Return CSV as streaming response
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={download_filename}"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except CSVProcessingError as e:
        # Handle CSV processing errors
        logger.log_error(f"CSV processing error for {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
        
    except pd.errors.EmptyDataError:
        logger.log_error(f"Empty CSV file uploaded: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="CSV file contains no data"
        )
        
    except pd.errors.ParserError as e:
        logger.log_error(f"CSV parsing error for {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"CSV parsing error: {str(e)}"
        )
        
    except Exception as e:
        # Handle unexpected errors
        logger.log_error(f"Unexpected error processing CSV {file.filename}", e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during CSV processing"
        )


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    description="Returns the current health status of the API and its components."
)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Current system health status with component details
    """
    try:
        # Check component health
        components = {
            "risk_processor": "healthy",
            "csv_processor": "healthy",
            "logging": "healthy"
        }
        
        # Check log files
        log_status = logger.check_log_files_exist()
        if not all(log_status.values()):
            components["logging"] = "warning"
        
        # Determine overall status
        overall_status = "healthy"
        if any(status == "warning" for status in components.values()):
            overall_status = "warning"
        elif any(status == "error" for status in components.values()):
            overall_status = "error"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            version=API_VERSION,
            components=components
        )
        
    except Exception as e:
        logger.log_error("Health check failed", e)
        return HealthCheckResponse(
            status="error",
            timestamp=datetime.utcnow().isoformat() + "Z",
            version=API_VERSION,
            components={"error": str(e)}
        )


@app.get(
    "/info",
    response_model=ProcessorInfoResponse,
    summary="Processor configuration information",
    description="Returns current configuration details of the risk processor and CSV processor."
)
async def get_processor_info() -> ProcessorInfoResponse:
    """
    Get current processor configuration information.
    
    Returns:
        Detailed configuration information for debugging and monitoring
    """
    try:
        # Get risk processor info
        processor_info = risk_processor.get_processor_info()
        csv_info = csv_processor.get_processing_info()
        
        return ProcessorInfoResponse(
            weights=processor_info["weights"],
            rules_count=processor_info["rules_count"],
            noise_level=processor_info["noise_level"],
            weather_categories=processor_info["weather_categories"],
            output_scale=processor_info["output_scale"],
            csv_max_workers=csv_info["max_workers"]
        )
        
    except Exception as e:
        logger.log_error("Failed to get processor info", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve processor information"
        )


@app.get(
    "/",
    summary="API root endpoint",
    description="Returns basic API information and links to documentation."
)
async def root():
    """
    Root endpoint with API information.
    
    Returns:
        Basic API information and navigation links
    """
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "description": "Risk Processing API for transforming raw risk indicators into normalized risk scores",
        "endpoints": {
            "process": "/process - Process single risk data (POST)",
            "process_csv": "/process-csv - Process CSV file upload (POST)",
            "health": "/health - Health check",
            "info": "/info - Processor configuration",
            "docs": "/docs - Interactive API documentation",
            "redoc": "/redoc - ReDoc API documentation"
        },
        "weather_categories": list(WEATHER_CATEGORIES.keys()),
        "required_csv_columns": CSV_REQUIRED_COLUMNS
    }


# Custom exception handlers for better error responses
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle custom validation errors."""
    logger.log_error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request, exc: PydanticValidationError):
    """Handle Pydantic validation errors."""
    error_details = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        error_details.append(f"{field}: {error['msg']}")
    
    error_message = "; ".join(error_details)
    logger.log_error(f"Pydantic validation error: {error_message}")
    
    return JSONResponse(
        status_code=400,
        content={"detail": error_message}
    )


@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """Handle internal server errors."""
    logger.log_error("Internal server error occurred", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )