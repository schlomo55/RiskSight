import pandas as pd
import pytest

from src.core.validators import CSVValidator, RiskDataValidator, ValidationError


def good(**over):
    data = {"crime_index": 5, "accident_rate": 4, "socioeconomic_level": 6, "weather": "Clear"}
    data.update(over)
    return data


@pytest.fixture
def validator():
    return RiskDataValidator()


class TestRiskDataValidator:
    def test_valid_data_is_cleaned_to_floats(self, validator):
        out = validator.validate_risk_data(good(city="  Paris  "))
        assert out == {
            "crime_index": 5.0,
            "accident_rate": 4.0,
            "socioeconomic_level": 6.0,
            "weather": "Clear",
            "city": "Paris",
        }

    def test_numeric_strings_are_accepted(self, validator):
        out = validator.validate_risk_data(good(crime_index="7.5"))
        assert out["crime_index"] == 7.5

    @pytest.mark.parametrize("field", ["crime_index", "accident_rate", "socioeconomic_level", "weather"])
    def test_missing_or_none_required_field(self, validator, field):
        data = good()
        del data[field]
        with pytest.raises(ValidationError, match=f"Missing required field: {field}"):
            validator.validate_risk_data(data)
        with pytest.raises(ValidationError, match=f"Missing required field: {field}"):
            validator.validate_risk_data(good(**{field: None}))

    @pytest.mark.parametrize(
        "field,value",
        [
            ("crime_index", 10.01),
            ("crime_index", -0.1),
            ("accident_rate", 10.5),
            ("accident_rate", -1),
            ("socioeconomic_level", 0.99),
            ("socioeconomic_level", 11),
        ],
    )
    def test_out_of_range(self, validator, field, value):
        with pytest.raises(ValidationError, match=f"{field} must be between"):
            validator.validate_risk_data(good(**{field: value}))

    @pytest.mark.parametrize(
        "field,value", [("crime_index", 0), ("crime_index", 10), ("accident_rate", 0),
                        ("accident_rate", 10), ("socioeconomic_level", 1), ("socioeconomic_level", 10)]
    )
    def test_range_boundaries_are_inclusive(self, validator, field, value):
        assert validator.validate_risk_data(good(**{field: value}))[field] == float(value)

    @pytest.mark.parametrize("field", ["crime_index", "accident_rate", "socioeconomic_level"])
    def test_non_numeric(self, validator, field):
        with pytest.raises(ValidationError, match=f"{field} must be a number"):
            validator.validate_risk_data(good(**{field: "high"}))

    def test_nan_and_inf_are_rejected(self, validator):
        with pytest.raises(ValidationError):
            validator.validate_risk_data(good(crime_index=float("nan")))
        with pytest.raises(ValidationError):
            validator.validate_risk_data(good(accident_rate=float("inf")))

    def test_unknown_weather(self, validator):
        with pytest.raises(ValidationError, match="Unknown weather: Foggy"):
            validator.validate_risk_data(good(weather="Foggy"))

    def test_weather_is_case_sensitive(self, validator):
        with pytest.raises(ValidationError, match="Unknown weather: clear"):
            validator.validate_risk_data(good(weather="clear"))

    def test_weather_whitespace_is_stripped(self, validator):
        assert validator.validate_risk_data(good(weather=" Rainy "))["weather"] == "Rainy"

    def test_weather_empty_and_non_string(self, validator):
        with pytest.raises(ValidationError, match="weather cannot be empty"):
            validator.validate_risk_data(good(weather="   "))
        with pytest.raises(ValidationError, match="weather must be a string"):
            validator.validate_risk_data(good(weather=3))

    def test_city_validation(self, validator):
        assert "city" not in validator.validate_risk_data(good(city=None))
        with pytest.raises(ValidationError, match="city cannot be empty"):
            validator.validate_risk_data(good(city="  "))
        with pytest.raises(ValidationError, match="cannot exceed 100"):
            validator.validate_risk_data(good(city="x" * 101))
        assert validator.validate_risk_data(good(city="x" * 100))["city"] == "x" * 100
        with pytest.raises(ValidationError, match="city must be a string"):
            validator.validate_risk_data(good(city=5))

    def test_all_errors_are_collected(self, validator):
        with pytest.raises(ValidationError) as exc:
            validator.validate_risk_data(good(crime_index=20, accident_rate=15, weather="Unknown"))
        msg = str(exc.value)
        assert "crime_index" in msg and "accident_rate" in msg and "Unknown weather" in msg


class TestCSVValidator:
    @pytest.fixture
    def csv_validator(self):
        return CSVValidator()

    def test_empty_dataframe(self, csv_validator):
        assert csv_validator.validate_csv_structure(pd.DataFrame()) == ["CSV file is empty"]

    def test_missing_columns(self, csv_validator):
        df = pd.DataFrame({"crime_index": [1], "city": ["A"]})
        errors = csv_validator.validate_csv_structure(df)
        assert len(errors) == 1
        assert errors[0].startswith("Missing required columns:")
        for col in ("accident_rate", "socioeconomic_level", "weather"):
            assert col in errors[0]

    def test_duplicate_columns(self, csv_validator):
        df = pd.DataFrame([[1, 2, 3, "Clear", 9]],
                          columns=["crime_index", "accident_rate", "socioeconomic_level", "weather", "weather"])
        errors = csv_validator.validate_csv_structure(df)
        assert errors == ["Duplicate column names: weather"]

    def test_completely_empty_rows_reported(self, csv_validator):
        df = pd.DataFrame({
            "crime_index": [1.0, None], "accident_rate": [1.0, None],
            "socioeconomic_level": [1.0, None], "weather": ["Clear", None],
        })
        assert csv_validator.validate_csv_structure(df) == ["Found 1 completely empty rows"]

    def test_valid_structure(self, csv_validator, valid_csv_text):
        from io import StringIO
        assert csv_validator.validate_csv_structure(pd.read_csv(StringIO(valid_csv_text))) == []

    def test_validate_csv_row_success_and_nan_handling(self, csv_validator):
        ok = csv_validator.validate_csv_row(pd.Series(good(city="X")), 0)
        assert ok["status"] == "SUCCESS" and ok["data"]["city"] == "X"

        bad = csv_validator.validate_csv_row(pd.Series(good(crime_index=float("nan"))), 3)
        assert bad["status"] == "ERROR"
        assert bad["row_index"] == 3
        assert "Missing required field: crime_index" in bad["error"]

    def test_validation_summary(self, csv_validator):
        results = [{"status": "SUCCESS"}, {"status": "ERROR"}, {"status": "SUCCESS"}]
        assert csv_validator.get_validation_summary(results) == {
            "total_rows": 3, "successful_rows": 2, "error_rows": 1}
        assert csv_validator.get_validation_summary([]) == {
            "total_rows": 0, "successful_rows": 0, "error_rows": 0}
