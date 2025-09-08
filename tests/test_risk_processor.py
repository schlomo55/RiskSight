"""
Comprehensive tests for the Risk Processor Engine.

Tests include deterministic processing, component calculations,
amplification rules, validation, and edge cases.
"""

import pytest
from src.core.risk_processor import RiskProcessor
from src.core.validators import ValidationError
from src.config.constants import DEFAULT_WEIGHTS, DEFAULT_RULES, WEATHER_CATEGORIES


class TestRiskProcessorBasics:
    """Test basic functionality of the RiskProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use deterministic mode (no noise) for predictable results
        self.processor = RiskProcessor(noise_level=0.0)
    
    def test_processor_initialization_defaults(self):
        """Test processor initializes with default configuration."""
        processor = RiskProcessor()
        
        assert processor.weights == DEFAULT_WEIGHTS
        assert processor.rules == DEFAULT_RULES
        assert processor.noise_level == 0.05  # Default noise level
        assert processor.weather_categories == WEATHER_CATEGORIES
    
    def test_processor_initialization_custom_weights(self):
        """Test processor initializes with custom weights."""
        custom_weights = {
            "crime_index": 0.4,
            "accident_rate": 0.3,
            "socioeconomic_level": 0.2,
            "weather": 0.1
        }
        
        processor = RiskProcessor(weights=custom_weights, noise_level=0.0)
        assert processor.weights == custom_weights
    
    def test_processor_initialization_custom_rules(self):
        """Test processor initializes with custom amplification rules."""
        custom_rules = [
            {
                "conditions": {"crime_index": ">5"},
                "multiplier": 1.2,
                "description": "High crime test rule"
            }
        ]
        
        processor = RiskProcessor(amplification_rules=custom_rules, noise_level=0.0)
        assert processor.rules == custom_rules
    
    def test_get_processor_info(self):
        """Test processor info method returns correct configuration."""
        info = self.processor.get_processor_info()
        
        assert "weights" in info
        assert "rules_count" in info
        assert "noise_level" in info
        assert "weather_categories" in info
        assert "output_scale" in info
        
        assert info["rules_count"] == len(DEFAULT_RULES)
        assert info["noise_level"] == 0.0  # Our test instance
        assert info["output_scale"] == 100


class TestRiskProcessorDeterministic:
    """Test deterministic processing with known inputs and expected outputs."""
    
    def setup_method(self):
        """Set up deterministic processor for predictable testing."""
        self.processor = RiskProcessor(noise_level=0.0)
    
    def test_simple_processing_no_amplification(self):
        """Test basic processing without triggering amplification rules."""
        input_data = {
            "city": "Test City",
            "crime_index": 5.0,
            "accident_rate": 4.0,
            "socioeconomic_level": 7,
            "weather": "Clear"
        }
        
        result = self.processor.process_risk_data(input_data)
        
        # Verify result structure
        assert "risk_score" in result
        assert "crime_index_component" in result
        assert "accident_rate_component" in result
        assert "socioeconomic_level_component" in result
        assert "weather_component" in result
        assert "city" in result
        
        # Verify city is preserved
        assert result["city"] == "Test City"
        
        # Verify component calculations
        # Crime: 5/10 = 0.5 → 50.0
        assert result["crime_index_component"] == 50.0
        
        # Accident: 4/10 = 0.4 → 40.0  
        assert result["accident_rate_component"] == 40.0
        
        # Socioeconomic: (11-7)/9 = 4/9 ≈ 0.444 → 44.44
        assert abs(result["socioeconomic_level_component"] - 44.44) < 0.01
        
        # Weather: "Clear" = 0.10 → 10.0
        assert result["weather_component"] == 10.0
        
        # Calculate expected final score
        # Base = (0.5 × 0.30) + (0.4 × 0.25) + (0.444 × 0.25) + (0.10 × 0.20)
        # Base = 0.15 + 0.10 + 0.111 + 0.02 = 0.381
        # Final = 0.381 × 100 = 38.1
        expected_score = 38.11
        assert abs(result["risk_score"] - expected_score) < 0.1
    
    def test_high_risk_scenario_with_amplification(self):
        """Test high-risk scenario that triggers amplification rules."""
        input_data = {
            "city": "High Risk City",
            "crime_index": 8.5,  # High crime (>7)
            "accident_rate": 7.0,
            "socioeconomic_level": 3,
            "weather": "Stormy"  # Severe weather
        }
        
        result = self.processor.process_risk_data(input_data)
        
        # Verify components
        assert result["crime_index_component"] == 85.0
        assert result["accident_rate_component"] == 70.0
        # Socioeconomic: (11-3)/9 = 8/9 ≈ 88.89
        assert abs(result["socioeconomic_level_component"] - 88.89) < 0.1
        assert result["weather_component"] == 90.0  # "Stormy" = 0.90
        
        # Base score calculation
        # Base = (0.85 × 0.30) + (0.70 × 0.25) + (0.889 × 0.25) + (0.90 × 0.20)
        # Base = 0.255 + 0.175 + 0.222 + 0.18 = 0.832
        
        # Amplification: Crime > 7 AND Weather in {"Stormy", "Snowy"} → × 1.15
        # Amplified = 0.832 × 1.15 = 0.957
        # Final = 0.957 × 100 = 95.7
        
        # The final score should be amplified
        expected_base = 83.2
        expected_amplified = expected_base * 1.15  # ≈ 95.68
        assert result["risk_score"] > expected_base  # Should be amplified
        assert abs(result["risk_score"] - expected_amplified) < 1.0
    
    def test_double_amplification_scenario(self):
        """Test scenario that triggers both amplification rules."""
        input_data = {
            "city": "Very High Risk",
            "crime_index": 9.0,  # High crime (>7)
            "accident_rate": 9.0,  # High accidents (>8)
            "socioeconomic_level": 2,  # Low socioeconomic (<3)
            "weather": "Snowy"  # Severe weather
        }
        
        result = self.processor.process_risk_data(input_data)
        
        # Both rules should trigger:
        # Rule 1: crime_index > 7 AND weather in {"Stormy", "Snowy"} → × 1.15
        # Rule 2: accident_rate > 8 AND socioeconomic_level < 3 → × 1.10
        # Total multiplier = 1.15 × 1.10 = 1.265
        
        # Base calculation
        # Crime: 90.0, Accident: 90.0, Socioeconomic: (11-2)/9 = 100.0, Weather: 70.0
        # Base = (0.90 × 0.30) + (0.90 × 0.25) + (1.0 × 0.25) + (0.70 × 0.20)
        # Base = 0.27 + 0.225 + 0.25 + 0.14 = 0.885 = 88.5
        
        expected_base = 88.5
        expected_amplified = expected_base * 1.265  # ≈ 111.95, capped at 100
        
        assert result["risk_score"] >= expected_base
        # Should be close to 100 (system caps at 100)
        assert result["risk_score"] <= 100.0


class TestRiskProcessorComponentCalculation:
    """Test individual component score calculations."""
    
    def setup_method(self):
        """Set up deterministic processor."""
        self.processor = RiskProcessor(noise_level=0.0)
    
    def test_crime_component_calculation(self):
        """Test crime index component normalization."""
        test_cases = [
            (0.0, 0.0),    # Minimum
            (5.0, 50.0),   # Mid-range  
            (10.0, 100.0)  # Maximum
        ]
        
        for crime_input, expected_component in test_cases:
            input_data = {
                "crime_index": crime_input,
                "accident_rate": 0.0,
                "socioeconomic_level": 10,  # Minimum risk (max prosperity)
                "weather": "Clear"
            }
            
            result = self.processor.process_risk_data(input_data)
            assert result["crime_index_component"] == expected_component
    
    def test_accident_component_calculation(self):
        """Test accident rate component normalization.""" 
        test_cases = [
            (0.0, 0.0),    # Minimum
            (2.5, 25.0),   # Quarter
            (10.0, 100.0)  # Maximum
        ]
        
        for accident_input, expected_component in test_cases:
            input_data = {
                "crime_index": 0.0,
                "accident_rate": accident_input,
                "socioeconomic_level": 10,  # Minimum risk
                "weather": "Clear"
            }
            
            result = self.processor.process_risk_data(input_data)
            assert result["accident_rate_component"] == expected_component
    
    def test_socioeconomic_component_calculation(self):
        """Test socioeconomic level component normalization (inverted)."""
        test_cases = [
            (10, 11.11),  # Max prosperity → min risk: (11-10)/9 = 1/9 ≈ 11.11%
            (5.5, 61.11), # Mid prosperity → mid risk: (11-5.5)/9 = 5.5/9 ≈ 61.11% 
            (1, 100.0)    # Min prosperity → max risk: (11-1)/9 = 10/9 ≈ 111%, capped at 100%
        ]
        
        for socio_input, expected_component in test_cases:
            input_data = {
                "crime_index": 0.0,
                "accident_rate": 0.0,
                "socioeconomic_level": socio_input,
                "weather": "Clear"
            }
            
            result = self.processor.process_risk_data(input_data)
            assert abs(result["socioeconomic_level_component"] - expected_component) < 0.1
    
    def test_weather_component_calculation(self):
        """Test weather component mapping."""
        weather_test_cases = [
            ("Clear", 10.0),    # 0.10 → 10.0
            ("Rainy", 50.0),    # 0.50 → 50.0
            ("Snowy", 70.0),    # 0.70 → 70.0
            ("Stormy", 90.0),   # 0.90 → 90.0
            ("Extreme", 95.0)   # 0.95 → 95.0
        ]
        
        for weather_input, expected_component in weather_test_cases:
            input_data = {
                "crime_index": 0.0,
                "accident_rate": 0.0,
                "socioeconomic_level": 10,  # Minimum risk
                "weather": weather_input
            }
            
            result = self.processor.process_risk_data(input_data)
            assert result["weather_component"] == expected_component


class TestRiskProcessorAmplificationRules:
    """Test amplification rule evaluation and application."""
    
    def setup_method(self):
        """Set up deterministic processor."""
        self.processor = RiskProcessor(noise_level=0.0)
    
    def test_no_amplification_rules_triggered(self):
        """Test that low-risk scenarios don't trigger amplification."""
        input_data = {
            "crime_index": 3.0,  # Low crime (≤7)
            "accident_rate": 4.0,  # Moderate accidents (≤8) 
            "socioeconomic_level": 8,  # High prosperity (≥3)
            "weather": "Clear"
        }
        
        # Calculate expected base score without amplification
        # Components: crime=30%, accident=40%, socio=33.33%, weather=10%
        # Base = (0.30×0.30) + (0.40×0.25) + (0.333×0.25) + (0.10×0.20) = 0.253
        # Final = 25.3
        
        result = self.processor.process_risk_data(input_data)
        expected_base = 25.33
        
        # Result should be close to base calculation (no amplification)
        assert abs(result["risk_score"] - expected_base) < 1.0
    
    def test_first_amplification_rule_only(self):
        """Test first rule: high crime + severe weather."""
        input_data = {
            "crime_index": 8.0,  # High crime (>7)
            "accident_rate": 3.0,  # Low accidents (≤8)
            "socioeconomic_level": 6,  # Moderate prosperity (≥3) 
            "weather": "Stormy"  # Severe weather
        }
        
        result = self.processor.process_risk_data(input_data)
        
        # Base calculation
        # Components: crime=80%, accident=30%, socio=55.56%, weather=90%
        # Base = (0.80×0.30) + (0.30×0.25) + (0.556×0.25) + (0.90×0.20) = 0.694
        
        base_score = 69.4
        expected_amplified = base_score * 1.15  # First rule multiplier
        
        assert result["risk_score"] > base_score
        assert abs(result["risk_score"] - expected_amplified) < 1.0
    
    def test_second_amplification_rule_only(self):
        """Test second rule: high accidents + low socioeconomic."""
        input_data = {
            "crime_index": 4.0,  # Moderate crime (≤7)
            "accident_rate": 9.0,  # High accidents (>8)
            "socioeconomic_level": 2,  # Low prosperity (<3)
            "weather": "Clear"  # Mild weather
        }
        
        result = self.processor.process_risk_data(input_data)
        
        # Base calculation
        # Components: crime=40%, accident=90%, socio=100%, weather=10%
        # Base = (0.40×0.30) + (0.90×0.25) + (1.0×0.25) + (0.10×0.20) = 0.595
        
        base_score = 59.5
        expected_amplified = base_score * 1.10  # Second rule multiplier
        
        assert result["risk_score"] > base_score
        assert abs(result["risk_score"] - expected_amplified) < 1.0
    
    def test_custom_amplification_rules(self):
        """Test processor with custom amplification rules."""
        custom_rules = [
            {
                "conditions": {"weather": {"Extreme"}},
                "multiplier": 1.5,
                "description": "Extreme weather penalty"
            }
        ]
        
        processor = RiskProcessor(amplification_rules=custom_rules, noise_level=0.0)
        
        input_data = {
            "crime_index": 5.0,
            "accident_rate": 5.0,
            "socioeconomic_level": 5,
            "weather": "Extreme"
        }
        
        result = processor.process_risk_data(input_data)
        
        # Should trigger custom rule with 1.5x multiplier
        # Base ≈ (0.5×0.3) + (0.5×0.25) + (0.667×0.25) + (0.95×0.2) = 0.654
        base_score = 65.4
        expected_amplified = base_score * 1.5
        
        assert result["risk_score"] > base_score
        assert abs(result["risk_score"] - expected_amplified) < 2.0


class TestRiskProcessorValidation:
    """Test input validation and error handling."""
    
    def setup_method(self):
        """Set up processor for validation testing."""
        self.processor = RiskProcessor(noise_level=0.0)
    
    def test_valid_input_processing(self):
        """Test that valid inputs process successfully."""
        valid_input = {
            "city": "Valid City",
            "crime_index": 5.5,
            "accident_rate": 3.2,
            "socioeconomic_level": 7,
            "weather": "Rainy"
        }
        
        # Should not raise any exceptions
        result = self.processor.process_risk_data(valid_input)
        assert isinstance(result, dict)
        assert "risk_score" in result
    
    def test_invalid_weather_category(self):
        """Test that invalid weather categories are rejected."""
        invalid_input = {
            "crime_index": 5.0,
            "accident_rate": 5.0,
            "socioeconomic_level": 5,
            "weather": "Foggy"  # Not in WEATHER_CATEGORIES
        }
        
        with pytest.raises(ValidationError, match="Unknown weather"):
            self.processor.process_risk_data(invalid_input)
    
    def test_crime_index_out_of_range(self):
        """Test that out-of-range crime index values are rejected."""
        # Test upper bound
        invalid_high = {
            "crime_index": 15.0,  # Above maximum of 10
            "accident_rate": 5.0,
            "socioeconomic_level": 5,
            "weather": "Clear"
        }
        
        with pytest.raises(ValidationError, match="crime_index must be between"):
            self.processor.process_risk_data(invalid_high)
        
        # Test lower bound
        invalid_low = {
            "crime_index": -1.0,  # Below minimum of 0
            "accident_rate": 5.0,
            "socioeconomic_level": 5,
            "weather": "Clear"
        }
        
        with pytest.raises(ValidationError, match="crime_index must be between"):
            self.processor.process_risk_data(invalid_low)
    
    def test_missing_required_fields(self):
        """Test that missing required fields are detected."""
        incomplete_input = {
            "crime_index": 5.0,
            "accident_rate": 5.0,
            # Missing socioeconomic_level and weather
        }
        
        with pytest.raises(ValidationError, match="Missing required field"):
            self.processor.process_risk_data(incomplete_input)
    
    def test_invalid_data_types(self):
        """Test that invalid data types are rejected."""
        invalid_type_input = {
            "crime_index": "high",  # Should be numeric
            "accident_rate": 5.0,
            "socioeconomic_level": 5,
            "weather": "Clear"
        }
        
        with pytest.raises(ValidationError, match="must be a number"):
            self.processor.process_risk_data(invalid_type_input)


class TestRiskProcessorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Set up deterministic processor."""
        self.processor = RiskProcessor(noise_level=0.0)
    
    def test_minimum_risk_scenario(self):
        """Test scenario with minimum possible risk values."""
        min_risk_input = {
            "crime_index": 0.0,  # Minimum crime
            "accident_rate": 0.0,  # Minimum accidents
            "socioeconomic_level": 10,  # Maximum prosperity (minimum risk)
            "weather": "Clear"  # Minimum weather risk
        }
        
        result = self.processor.process_risk_data(min_risk_input)
        
        # Should result in very low risk score
        assert result["risk_score"] < 15.0
        assert all(component <= 15.0 for key, component in result.items() 
                  if key.endswith("_component"))
    
    def test_maximum_risk_scenario(self):
        """Test scenario with maximum possible risk values."""
        max_risk_input = {
            "crime_index": 10.0,  # Maximum crime
            "accident_rate": 10.0,  # Maximum accidents
            "socioeconomic_level": 1,  # Minimum prosperity (maximum risk)
            "weather": "Extreme"  # Maximum weather risk
        }
        
        result = self.processor.process_risk_data(max_risk_input)
        
        # Should result in very high risk score (possibly amplified to cap)
        assert result["risk_score"] >= 85.0
        assert result["risk_score"] <= 100.0  # System should cap at 100
    
    def test_boundary_values_crime_index(self):
        """Test exact boundary values for crime index."""
        # Test exact boundaries
        boundary_cases = [0.0, 10.0]  # Min and max allowed values
        
        for crime_value in boundary_cases:
            input_data = {
                "crime_index": crime_value,
                "accident_rate": 5.0,
                "socioeconomic_level": 5,
                "weather": "Clear"
            }
            
            # Should process without error
            result = self.processor.process_risk_data(input_data)
            assert isinstance(result, dict)
    
    def test_boundary_values_socioeconomic(self):
        """Test exact boundary values for socioeconomic level."""
        boundary_cases = [1, 10]  # Min and max allowed values
        
        for socio_value in boundary_cases:
            input_data = {
                "crime_index": 5.0,
                "accident_rate": 5.0,
                "socioeconomic_level": socio_value,
                "weather": "Clear"
            }
            
            result = self.processor.process_risk_data(input_data)
            assert isinstance(result, dict)


class TestRiskProcessorNoise:
    """Test statistical noise functionality."""
    
    def test_deterministic_mode_reproducible(self):
        """Test that deterministic mode produces identical results."""
        processor = RiskProcessor(noise_level=0.0)
        
        input_data = {
            "crime_index": 6.5,
            "accident_rate": 4.2,
            "socioeconomic_level": 7,
            "weather": "Rainy"
        }
        
        # Process same input multiple times
        results = [processor.process_risk_data(input_data) for _ in range(5)]
        
        # All results should be identical
        first_score = results[0]["risk_score"]
        for result in results[1:]:
            assert result["risk_score"] == first_score
    
    def test_noise_mode_variability(self):
        """Test that noise mode produces varied results."""
        processor = RiskProcessor(noise_level=0.1)  # 10% noise
        
        input_data = {
            "crime_index": 5.0,
            "accident_rate": 5.0,
            "socioeconomic_level": 5,
            "weather": "Clear"
        }
        
        # Process same input multiple times
        results = [processor.process_risk_data(input_data) for _ in range(10)]
        scores = [result["risk_score"] for result in results]
        
        # Results should vary due to noise
        # At least some should be different
        unique_scores = set(scores)
        assert len(unique_scores) > 1, "Noise should produce varied results"
        
        # But all should be within reasonable bounds
        for score in scores:
            assert 0 <= score <= 100
    
    def test_deterministic_mode_toggle(self):
        """Test switching between deterministic and noise modes."""
        processor = RiskProcessor(noise_level=0.1)
        
        input_data = {
            "crime_index": 5.0,
            "accident_rate": 5.0, 
            "socioeconomic_level": 5,
            "weather": "Clear"
        }
        
        # Switch to deterministic mode
        processor.set_deterministic_mode(True)
        
        # Should now produce consistent results
        results = [processor.process_risk_data(input_data) for _ in range(3)]
        scores = [result["risk_score"] for result in results]
        
        # All should be identical now
        assert len(set(scores)) == 1
        
        # Switch back to noise mode
        processor.set_deterministic_mode(False)
        
        # Should vary again (though we can't guarantee difference in small sample)
        # Just verify it doesn't crash
        result = processor.process_risk_data(input_data)
        assert isinstance(result["risk_score"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])