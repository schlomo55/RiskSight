import pandas as pd
import pytest

from src.core.risk_processor import RiskProcessor
from src.services.csv_processor import CSVProcessingError, CSVProcessor

HEADER = "city,crime_index,accident_rate,socioeconomic_level,weather\n"


@pytest.fixture
def processor():
    return CSVProcessor(RiskProcessor(noise_level=0.0))


class TestValidSample:
    def test_all_rows_succeed(self, processor, valid_csv_text):
        out = processor.process_csv_file(valid_csv_text, "sample_valid_data.csv")
        assert len(out) == 50
        assert (out["processing_status"] == "SUCCESS").all()
        assert (out["error_message"] == "").all()
        scores = pd.to_numeric(out["risk_score"])
        assert scores.between(0, 100).all()

    def test_output_columns_and_order(self, processor, valid_csv_text):
        out = processor.process_csv_file(valid_csv_text)
        assert list(out.columns) == [
            "city", "crime_index", "accident_rate", "socioeconomic_level", "weather",
            "crime_index_component", "accident_rate_component",
            "socioeconomic_level_component", "weather_component",
            "processing_status", "error_message", "risk_score"]

    def test_row_values_match_direct_processing(self, processor, valid_csv_text):
        out = processor.process_csv_file(valid_csv_text)
        direct = RiskProcessor(noise_level=0.0).process_risk_data(
            {"crime_index": 7.8, "accident_rate": 6.5, "socioeconomic_level": 5, "weather": "Rainy"})
        row = out.iloc[0]
        assert row["city"] == "New York City"
        assert float(row["risk_score"]) == direct["risk_score"]

    def test_row_order_is_preserved(self, processor, valid_csv_text):
        out = processor.process_csv_file(valid_csv_text)
        assert out["city"].iloc[0] == "New York City"
        assert out["city"].iloc[-1] == "Cleveland"


class TestErrorSample:
    @pytest.fixture
    def result(self, processor, error_csv_text):
        return processor.process_csv_file(error_csv_text, "sample_error_data.csv").set_index("city")

    def test_batch_is_not_aborted_and_rows_retained(self, result):
        assert len(result) == 25

    @pytest.mark.parametrize("city,fragment", [
        ("Out of Range Crime", "crime_index must be between"),
        ("Invalid Weather", "Unknown weather: Foggy"),
        ("Missing Crime", "Missing required field: crime_index"),
        ("Out of Range Accident", "accident_rate must be between"),
        ("Invalid Socioeconomic", "socioeconomic_level must be between"),
        ("String Crime", "crime_index must be a number"),
        ("Negative Values", "crime_index must be between"),
        ("Out of Range Socio High", "socioeconomic_level must be between"),
        ("Empty Weather", "Missing required field: weather"),
        ("String Accident", "accident_rate must be a number"),
        ("Missing Socioeconomic", "Missing required field: socioeconomic_level"),
        ("Invalid Weather 2", "Unknown weather: Sunny"),
        ("Case Sensitive Weather", "Unknown weather: clear"),
        ("Special Characters", "Unknown weather: Storm@"),
        ("Float String Mix", "accident_rate must be a number"),
    ])
    def test_error_rows(self, result, city, fragment):
        row = result.loc[city]
        assert row["processing_status"] == "ERROR"
        assert fragment in row["error_message"]
        assert row["risk_score"] == ""

    def test_multiple_errors_are_joined(self, result):
        msg = result.loc["Multiple Errors"]["error_message"]
        assert "crime_index" in msg and "accident_rate" in msg and "Unknown weather" in msg

    def test_missing_all_data_row(self, result):
        row = result.loc["Missing All Data"]
        assert row["processing_status"] == "ERROR"
        assert "Missing required field" in row["error_message"]

    @pytest.mark.parametrize("city", [
        "Valid City 1", "Valid City 2", "Valid City 3", "Valid City 4", "Mixed Valid/Invalid 1",
        "Boundary Test High", "Boundary Test Low"])
    def test_valid_rows_succeed(self, result, city):
        row = result.loc[city]
        assert row["processing_status"] == "SUCCESS"
        assert 0 <= float(row["risk_score"]) <= 100

    def test_boundary_scores(self, result):
        # crime/accident/weather at maximum, socioeconomic level 10 (lowest risk) + 1.15 rule
        expected = (0.30 + 0.25 + (1 / 9) * 0.25 + 0.95 * 0.20) * 1.15 * 100
        assert float(result.loc["Boundary Test High"]["risk_score"]) == pytest.approx(round(expected, 2))
        # crime/accident 0, socioeconomic level 1, Clear weather + 0.9 rule
        expected = (0 + 0 + (10 / 9) * 0.25 + 0.10 * 0.20) * 0.9 * 100
        assert float(result.loc["Boundary Test Low"]["risk_score"]) == pytest.approx(round(expected, 2))

    def test_status_counts(self, result):
        counts = result["processing_status"].value_counts().to_dict()
        assert counts == {"ERROR": 17, "SUCCESS": 8}

    @pytest.mark.xfail(
        reason="Possible bug: examples/sample_error_data.csv labels the row 'Decimal Socio Error' "
               "(socioeconomic_level=6.5) as an error, but the validator accepts any float in 1-10, "
               "so the row is processed successfully.",
        strict=True,
    )
    def test_decimal_socioeconomic_level_is_rejected(self, result):
        assert result.loc["Decimal Socio Error"]["processing_status"] == "ERROR"


class TestStructureErrors:
    def test_empty_content(self, processor):
        with pytest.raises(CSVProcessingError):
            processor.process_csv_file("")

    def test_header_only(self, processor):
        with pytest.raises(CSVProcessingError, match="no data"):
            processor.process_csv_file(HEADER)

    def test_missing_required_columns(self, processor):
        with pytest.raises(CSVProcessingError, match="Missing required columns"):
            processor.process_csv_file("city,crime_index\nA,5\n")

    def test_city_column_is_optional(self, processor):
        out = processor.process_csv_file("crime_index,accident_rate,socioeconomic_level,weather\n5,4,6,Clear\n")
        assert out["processing_status"].tolist() == ["SUCCESS"]
        assert out["city"].tolist() == [""]

    def test_validate_csv_structure_helper(self, processor, valid_csv_text):
        assert processor.validate_csv_structure(valid_csv_text) == []
        assert processor.validate_csv_structure("   ") == ["CSV file is empty"]
        assert "Missing required columns" in processor.validate_csv_structure("a,b\n1,2\n")[0]

    def test_malformed_rows_are_skipped(self, processor):
        content = HEADER + "A,5,4,6,Clear\nB,5,4,6,Clear,extra,fields\nC,6,5,7,Rainy\n"
        out = processor.process_csv_file(content)
        assert out["city"].tolist() == ["A", "C"]


class TestConfig:
    def test_worker_count_bounds(self, processor):
        processor.set_worker_count(4)
        assert processor.max_workers == 4
        for bad in (0, 17):
            with pytest.raises(ValueError):
                processor.set_worker_count(bad)

    def test_single_worker_gives_same_result(self, processor, valid_csv_text):
        a = processor.process_csv_file(valid_csv_text)
        processor.set_worker_count(1)
        b = processor.process_csv_file(valid_csv_text)
        pd.testing.assert_frame_equal(a, b)

    def test_processing_info(self, processor):
        info = processor.get_processing_info()
        assert "city" in info["optional_columns"]
        assert info["risk_processor_info"]["rules_count"] == 2
