#!/bin/bash

# cURL Usage Examples for the Risk Processing API
# 
# This script demonstrates how to interact with the Risk Processing API
# using cURL commands for various scenarios including single risk processing,
# CSV file uploads, health checks, and error handling.
#
# Prerequisites:
# - API server running at http://localhost:8000
# - cURL installed on your system
# - Sample CSV files (sample_valid_data.csv, sample_error_data.csv)

# API Configuration
API_BASE_URL="http://localhost:8000"

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored headers
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print info messages
print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Function to check if API is available
check_api_availability() {
    print_header "Checking API Availability"
    
    response=$(curl -s -w "%{http_code}" -o /dev/null "$API_BASE_URL/health" || echo "000")
    
    if [ "$response" = "200" ]; then
        print_success "API is available at $API_BASE_URL"
        return 0
    else
        print_error "API not available at $API_BASE_URL (HTTP $response)"
        print_info "Please start the API server first:"
        print_info "  python main.py"
        return 1
    fi
}

# Example 1: API Root Information
example_1_root_info() {
    print_header "Example 1: API Root Information"
    
    print_info "Getting API root information..."
    curl -s -X GET "$API_BASE_URL/" \
         -H "Accept: application/json" | \
    python -m json.tool 2>/dev/null || echo "Response received"
    
    echo ""
}

# Example 2: Health Check
example_2_health_check() {
    print_header "Example 2: Health Check"
    
    print_info "Checking API health status..."
    curl -s -X GET "$API_BASE_URL/health" \
         -H "Accept: application/json" | \
    python -m json.tool 2>/dev/null || echo "Health check completed"
    
    echo ""
}

# Example 3: Processor Configuration Info
example_3_processor_info() {
    print_header "Example 3: Processor Configuration Info"
    
    print_info "Getting processor configuration..."
    curl -s -X GET "$API_BASE_URL/info" \
         -H "Accept: application/json" | \
    python -m json.tool 2>/dev/null || echo "Configuration retrieved"
    
    echo ""
}

# Example 4: Basic Single Risk Processing
example_4_single_risk_processing() {
    print_header "Example 4: Basic Single Risk Processing"
    
    print_info "Processing single risk assessment for San Francisco..."
    
    curl -s -X POST "$API_BASE_URL/process" \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{
           "city": "San Francisco",
           "crime_index": 5.8,
           "accident_rate": 6.3,
           "socioeconomic_level": 8,
           "weather": "Clear"
         }' | \
    python -m json.tool 2>/dev/null || echo "Risk assessment completed"
    
    echo ""
}

# Example 5: High Risk Scenario with Amplification
example_5_high_risk_scenario() {
    print_header "Example 5: High Risk Scenario with Amplification"
    
    print_info "Processing high-risk scenario that should trigger amplification rules..."
    print_info "- High crime (>7) + Severe weather → ×1.15 multiplier"
    print_info "- High accidents (>8) + Low socioeconomic (<3) → ×1.10 multiplier"
    
    curl -s -X POST "$API_BASE_URL/process" \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{
           "city": "Detroit",
           "crime_index": 9.1,
           "accident_rate": 8.2,
           "socioeconomic_level": 2,
           "weather": "Stormy"
         }' | \
    python -m json.tool 2>/dev/null || echo "High-risk assessment completed"
    
    echo ""
}

# Example 6: Validation Error - Invalid Weather
example_6_validation_error_weather() {
    print_header "Example 6: Validation Error - Invalid Weather"
    
    print_info "Testing validation with invalid weather category 'Foggy'..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_BASE_URL/process" \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{
           "city": "Test City",
           "crime_index": 5.0,
           "accident_rate": 4.0,
           "socioeconomic_level": 6,
           "weather": "Foggy"
         }')
    
    # Extract the body and the status
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
    
    if [ "$status" = "400" ]; then
        print_success "Expected validation error received"
    else
        print_error "Unexpected status code: $status"
    fi
    
    echo ""
}

# Example 7: Validation Error - Out of Range
example_7_validation_error_range() {
    print_header "Example 7: Validation Error - Out of Range Values"
    
    print_info "Testing validation with crime_index = 15.0 (above maximum of 10)..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_BASE_URL/process" \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{
           "city": "Test City",
           "crime_index": 15.0,
           "accident_rate": 4.0,
           "socioeconomic_level": 6,
           "weather": "Clear"
         }')
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
    
    if [ "$status" = "400" ] || [ "$status" = "422" ]; then
        print_success "Expected validation error received"
    else
        print_error "Unexpected status code: $status"
    fi
    
    echo ""
}

# Example 8: Missing Required Fields
example_8_missing_fields() {
    print_header "Example 8: Missing Required Fields"
    
    print_info "Testing validation with missing required fields..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_BASE_URL/process" \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{
           "city": "Test City",
           "crime_index": 5.0,
           "accident_rate": 4.0
         }')
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
    
    if [ "$status" = "422" ]; then
        print_success "Expected validation error received"
    else
        print_error "Unexpected status code: $status"
    fi
    
    echo ""
}

# Example 9: CSV File Upload - Valid Data
example_9_csv_upload_valid() {
    print_header "Example 9: CSV File Upload - Valid Data"
    
    if [ ! -f "sample_valid_data.csv" ]; then
        print_error "sample_valid_data.csv not found"
        print_info "Please ensure the sample CSV files are in the current directory"
        return 1
    fi
    
    print_info "Uploading and processing sample_valid_data.csv..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_BASE_URL/process-csv" \
         -H "Accept: text/csv" \
         -F "file=@sample_valid_data.csv")
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    
    if [ "$status" = "200" ]; then
        print_success "CSV processed successfully"
        
        # Save the processed CSV to a file
        echo "$body" > processed_valid_data_curl.csv
        print_info "Processed CSV saved as: processed_valid_data_curl.csv"
        
        # Show some statistics
        total_lines=$(echo "$body" | wc -l)
        success_count=$(echo "$body" | grep -c "SUCCESS" || echo "0")
        error_count=$(echo "$body" | grep -c "ERROR" || echo "0")
        
        echo "Processing Statistics:"
        echo "  Total rows: $((total_lines - 1))"
        echo "  Successful: $success_count"
        echo "  Errors: $error_count"
        
        # Show first few lines of results
        echo -e "\nFirst 5 processed rows:"
        echo "$body" | head -6
        
    else
        print_error "CSV processing failed with status $status"
        echo "$body"
    fi
    
    echo ""
}

# Example 10: CSV File Upload - Error Data
example_10_csv_upload_errors() {
    print_header "Example 10: CSV File Upload - Error Handling"
    
    if [ ! -f "sample_error_data.csv" ]; then
        print_error "sample_error_data.csv not found"
        print_info "Please ensure the sample CSV files are in the current directory"
        return 1
    fi
    
    print_info "Uploading and processing sample_error_data.csv (contains intentional errors)..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_BASE_URL/process-csv" \
         -H "Accept: text/csv" \
         -F "file=@sample_error_data.csv")
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    
    if [ "$status" = "200" ]; then
        print_success "CSV processed successfully (with expected errors)"
        
        # Save the processed CSV to a file
        echo "$body" > processed_error_data_curl.csv
        print_info "Processed CSV saved as: processed_error_data_curl.csv"
        
        # Show error statistics
        total_lines=$(echo "$body" | wc -l)
        success_count=$(echo "$body" | grep -c "SUCCESS" || echo "0")
        error_count=$(echo "$body" | grep -c "ERROR" || echo "0")
        
        echo "Processing Statistics:"
        echo "  Total rows: $((total_lines - 1))"
        echo "  Successful: $success_count"
        echo "  Errors: $error_count"
        echo "  Error rate: $(echo "scale=1; $error_count * 100 / ($total_lines - 1)" | bc -l 2>/dev/null || echo "N/A")%"
        
        # Show some error examples
        echo -e "\nSample error rows:"
        echo "$body" | grep "ERROR" | head -3
        
    else
        print_error "CSV processing failed with status $status"
        echo "$body"
    fi
    
    echo ""
}

# Example 11: CSV Upload - Invalid Structure
example_11_csv_invalid_structure() {
    print_header "Example 11: CSV Upload - Invalid Structure"
    
    print_info "Creating temporary CSV with missing required columns..."
    
    # Create a temporary CSV with missing columns
    cat > temp_invalid.csv << EOF
city,crime_index,weather
New York,7.5,Rainy
Los Angeles,5.8,Clear
EOF
    
    print_info "Uploading CSV with invalid structure (missing required columns)..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_BASE_URL/process-csv" \
         -H "Accept: application/json" \
         -F "file=@temp_invalid.csv")
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
    
    if [ "$status" = "400" ]; then
        print_success "Expected structural error received"
    else
        print_error "Unexpected status code: $status"
    fi
    
    # Clean up temporary file
    rm -f temp_invalid.csv
    
    echo ""
}

# Example 12: Non-CSV File Upload
example_12_non_csv_upload() {
    print_header "Example 12: Non-CSV File Upload"
    
    print_info "Creating temporary text file..."
    
    # Create a temporary non-CSV file
    echo "This is not a CSV file" > temp_text.txt
    
    print_info "Uploading non-CSV file (should be rejected)..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "$API_BASE_URL/process-csv" \
         -H "Accept: application/json" \
         -F "file=@temp_text.txt")
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
    
    if [ "$status" = "400" ]; then
        print_success "Expected file type error received"
    else
        print_error "Unexpected status code: $status"
    fi
    
    # Clean up temporary file
    rm -f temp_text.txt
    
    echo ""
}

# Example 13: Boundary Value Testing
example_13_boundary_values() {
    print_header "Example 13: Boundary Value Testing"
    
    print_info "Testing minimum boundary values..."
    curl -s -X POST "$API_BASE_URL/process" \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{
           "city": "Min Values Test",
           "crime_index": 0.0,
           "accident_rate": 0.0,
           "socioeconomic_level": 1,
           "weather": "Clear"
         }' | \
    python -m json.tool 2>/dev/null || echo "Min values test completed"
    
    echo ""
    
    print_info "Testing maximum boundary values..."
    curl -s -X POST "$API_BASE_URL/process" \
         -H "Content-Type: application/json" \
         -H "Accept: application/json" \
         -d '{
           "city": "Max Values Test",
           "crime_index": 10.0,
           "accident_rate": 10.0,
           "socioeconomic_level": 10,
           "weather": "Extreme"
         }' | \
    python -m json.tool 2>/dev/null || echo "Max values test completed"
    
    echo ""
}

# Example 14: Method Not Allowed
example_14_method_not_allowed() {
    print_header "Example 14: Method Not Allowed"
    
    print_info "Testing GET request on POST-only endpoint..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$API_BASE_URL/process")
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    echo "$body"
    
    if [ "$status" = "405" ]; then
        print_success "Expected 405 Method Not Allowed received"
    else
        print_error "Unexpected status code: $status"
    fi
    
    echo ""
}

# Example 15: 404 Not Found
example_15_not_found() {
    print_header "Example 15: 404 Not Found"
    
    print_info "Testing request to non-existent endpoint..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$API_BASE_URL/nonexistent")
    
    body=$(echo $response | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    status=$(echo $response | grep -o '[0-9]\{3\}$')
    
    echo "HTTP Status: $status"
    echo "$body"
    
    if [ "$status" = "404" ]; then
        print_success "Expected 404 Not Found received"
    else
        print_error "Unexpected status code: $status"
    fi
    
    echo ""
}

# Main function to run all examples
main() {
    echo -e "${BLUE}Risk Processing API - cURL Usage Examples${NC}"
    echo "=========================================="
    
    # Check API availability first
    if ! check_api_availability; then
        exit 1
    fi
    
    # Run all examples
    example_1_root_info
    example_2_health_check
    example_3_processor_info
    example_4_single_risk_processing
    example_5_high_risk_scenario
    example_6_validation_error_weather
    example_7_validation_error_range
    example_8_missing_fields
    example_9_csv_upload_valid
    example_10_csv_upload_errors
    example_11_csv_invalid_structure
    example_12_non_csv_upload
    example_13_boundary_values
    example_14_method_not_allowed
    example_15_not_found
    
    print_header "All Examples Completed"
    print_success "All cURL examples have been executed!"
    print_info "Check the generated files:"
    print_info "  - processed_valid_data_curl.csv"
    print_info "  - processed_error_data_curl.csv"
}

# Check if script is being run directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi