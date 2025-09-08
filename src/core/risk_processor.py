"""
Main Risk Processing Engine for transforming raw risk indicators.

This module contains the core business logic for processing risk data,
applying transformations, calculating component scores, and generating
final aggregated risk scores with configurable rules and weights.
"""

import random
from typing import Dict, List, Optional, Any, Union
from src.core.validators import RiskDataValidator, ValidationError
from src.config.constants import (
    DEFAULT_WEIGHTS, DEFAULT_RULES, WEATHER_CATEGORIES,
    DEFAULT_NOISE_LEVEL, OUTPUT_SCALE
)


class RiskProcessor:
    """
    Main risk processing engine that transforms raw risk indicators
    into normalized risk scores with configurable weights and rules.
    
    Features:
    - Multi-stage transformation pipeline
    - Extensible amplification rules
    - Statistical noise simulation
    - Component score breakdown
    - Configurable weights and parameters
    """
    
    def __init__(self, 
                 weights: Optional[Dict[str, float]] = None,
                 amplification_rules: Optional[List[Dict]] = None,
                 noise_level: float = DEFAULT_NOISE_LEVEL):
        """
        Initialize the risk processor with configurable parameters.
        
        Args:
            weights: Component weights (defaults from constants.py)
            amplification_rules: Risk interaction rules (defaults from constants.py)
            noise_level: Statistical noise level (0.0 = deterministic)
        """
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.rules = amplification_rules or DEFAULT_RULES.copy()
        self.noise_level = noise_level
        self.weather_categories = WEATHER_CATEGORIES
        self.validator = RiskDataValidator()
        
        # Validate weights sum to reasonable value
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            print(f"Warning: Component weights sum to {total_weight}, not 1.0")
    
    def process_risk_data(self, raw_data: Dict[str, Any]) -> Dict[str, Union[float, str]]:
        """
        Process raw risk indicators into normalized risk score.
        
        This is the main entry point for risk processing that orchestrates
        the entire transformation pipeline.
        
        Args:
            raw_data: Dictionary containing raw risk indicators
            
        Returns:
            Dictionary with final risk_score and component breakdown
            
        Raises:
            ValidationError: If input validation fails
            ValueError: If processing encounters invalid data
        """
        try:
            # Stage 1: Validate and clean inputs
            validated_data = self.validator.validate_risk_data(raw_data)
            
            # Stage 2: Calculate normalized component scores (0-1 scale)
            components = self._calculate_component_scores(validated_data)
            
            # Stage 3: Apply weighted aggregation
            base_score = self._calculate_weighted_score(components)
            
            # Stage 4: Apply amplification rules
            amplified_score = self._apply_amplification_rules(base_score, validated_data)
            
            # Stage 5: Add statistical noise (if configured)
            noisy_score = self._add_statistical_noise(amplified_score)
            
            # Stage 6: Scale to output range and prepare final result
            final_result = self._prepare_final_result(noisy_score, components, validated_data)
            
            return final_result
            
        except ValidationError:
            # Re-raise validation errors as-is for proper error handling
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ValueError(f"Risk processing failed: {str(e)}")
    
    def _calculate_component_scores(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate normalized component scores (0-1 scale).
        
        Transforms raw indicators into normalized risk components:
        - Crime index: Direct normalization (0-10 -> 0-1)
        - Accident rate: Direct normalization (0-10 -> 0-1)  
        - Socioeconomic level: Inverse normalization (higher level = lower risk)
        - Weather: Lookup from weather categories mapping
        
        Args:
            data: Validated input data
            
        Returns:
            Dictionary of component scores (0-1 scale)
        """
        components = {}
        
        # Normalize crime index (0-10 scale to 0-1)
        components["crime_index"] = data["crime_index"] / 10.0
        
        # Normalize accident rate (0-10 scale to 0-1)
        components["accident_rate"] = data["accident_rate"] / 10.0
        
        # Normalize socioeconomic level (1-10 scale, inverted to 0-1)
        # Higher socioeconomic level means lower risk
        components["socioeconomic_level"] = (11 - data["socioeconomic_level"]) / 9.0
        
        # Weather component from predefined mapping
        components["weather"] = self.weather_categories[data["weather"]]
        
        return components
    
    def _calculate_weighted_score(self, components: Dict[str, float]) -> float:
        """
        Calculate weighted aggregation of component scores.
        
        Args:
            components: Dictionary of component scores (0-1 scale)
            
        Returns:
            Weighted score (0-1 scale)
        """
        weighted_score = sum(
            components[component] * self.weights[component]
            for component in components
        )
        
        # Ensure score stays within bounds
        return max(0.0, min(1.0, weighted_score))
    
    def _apply_amplification_rules(self, base_score: float, data: Dict[str, Any]) -> float:
        """
        Apply configurable amplification rules to the base score.
        
        Rules are evaluated in order and multipliers are applied cumulatively.
        Each rule can check multiple conditions that must all be satisfied.
        
        Args:
            base_score: Base weighted score (0-1 scale)
            data: Validated input data
            
        Returns:
            Amplified score (may exceed 1.0, will be clamped later)
        """
        amplified_score = base_score
        applied_rules = []
        
        for rule in self.rules:
            if self._evaluate_rule_conditions(rule["conditions"], data):
                amplified_score *= rule["multiplier"]
                applied_rules.append({
                    "description": rule.get("description", "Unnamed rule"),
                    "multiplier": rule["multiplier"]
                })
        
        # Log applied rules for transparency
        if applied_rules:
            rule_descriptions = [f"{r['description']} (×{r['multiplier']})" for r in applied_rules]
            print(f"Applied amplification rules: {'; '.join(rule_descriptions)}")
        
        return amplified_score
    
    def _evaluate_rule_conditions(self, conditions: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """
        Evaluate whether rule conditions are satisfied.
        
        Supports:
        - Comparison operators: ">7", "<3", "=5"
        - Set membership: {"Stormy", "Snowy"}
        
        Args:
            conditions: Dictionary of field conditions
            data: Input data to check against
            
        Returns:
            True if all conditions are satisfied, False otherwise
        """
        for field, condition in conditions.items():
            if field not in data:
                return False
            
            field_value = data[field]
            
            if isinstance(condition, str):
                # Handle comparison operators (">7", "<3", "=5")
                if len(condition) < 2:
                    continue
                
                operator = condition[0]
                try:
                    threshold = float(condition[1:])
                except ValueError:
                    continue
                
                if operator == ">" and not (field_value > threshold):
                    return False
                elif operator == "<" and not (field_value < threshold):
                    return False
                elif operator == "=" and not (field_value == threshold):
                    return False
                    
            elif isinstance(condition, (set, list)):
                # Handle set membership checks
                if field_value not in condition:
                    return False
            
            elif isinstance(condition, (int, float)):
                # Handle direct value comparison
                if field_value != condition:
                    return False
        
        return True
    
    def _add_statistical_noise(self, score: float) -> float:
        """
        Add statistical noise to simulate real-world inconsistencies.
        
        Noise is uniformly distributed within ±noise_level range.
        If noise_level is 0.0, no noise is added (deterministic mode).
        
        Args:
            score: Input score
            
        Returns:
            Score with added noise, clamped to [0, 1] range
        """
        if self.noise_level == 0.0:
            return score  # Deterministic mode for testing
        
        # Add uniform random noise
        noise = random.uniform(-self.noise_level, self.noise_level)
        noisy_score = score + noise
        
        # Clamp to valid range
        return max(0.0, min(1.0, noisy_score))
    
    def _prepare_final_result(self, 
                            final_score: float, 
                            components: Dict[str, float], 
                            input_data: Dict[str, Any]) -> Dict[str, Union[float, str]]:
        """
        Prepare the final result with proper scaling and formatting.
        
        Args:
            final_score: Final aggregated score (0-1 scale)
            components: Component scores (0-1 scale)
            input_data: Original input data
            
        Returns:
            Dictionary with scaled scores and metadata
        """
        # Scale final score to output range (0-100)
        scaled_score = min(max(final_score * OUTPUT_SCALE, 0), OUTPUT_SCALE)
        
        # Scale component scores to output range and clamp to validation limits
        # This prevents validation errors when component values exceed 100 due to amplification
        scaled_components = {
            f"{component}_component": round(
                min(max(score * OUTPUT_SCALE, 0), OUTPUT_SCALE), 2
            )
            for component, score in components.items()
        }
        
        # Prepare final result
        result = {
            "risk_score": round(scaled_score, 2),
            **scaled_components
        }
        
        # Add city if provided
        if "city" in input_data:
            result["city"] = input_data["city"]
        
        return result
    
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get information about the current processor configuration.
        
        Returns:
            Dictionary with processor configuration details
        """
        return {
            "weights": self.weights.copy(),
            "rules_count": len(self.rules),
            "noise_level": self.noise_level,
            "weather_categories": list(self.weather_categories.keys()),
            "output_scale": OUTPUT_SCALE
        }
    
    def set_deterministic_mode(self, deterministic: bool = True):
        """
        Enable/disable deterministic mode for testing.
        
        In deterministic mode, noise_level is set to 0.0 to ensure
        reproducible results for testing purposes.
        
        Args:
            deterministic: If True, disable noise; if False, restore original noise level
        """
        if deterministic:
            self._original_noise_level = self.noise_level
            self.noise_level = 0.0
        else:
            if hasattr(self, '_original_noise_level'):
                self.noise_level = self._original_noise_level
            else:
                self.noise_level = DEFAULT_NOISE_LEVEL