import pytest

from src.config.constants import DEFAULT_WEIGHTS
from src.core.risk_processor import RiskProcessor
from src.core.validators import ValidationError


def data(**over):
    d = {"crime_index": 5, "accident_rate": 4, "socioeconomic_level": 6, "weather": "Clear"}
    d.update(over)
    return d


@pytest.fixture
def proc():
    return RiskProcessor(noise_level=0.0)


class TestComponents:
    def test_component_normalisation(self, proc):
        comps = proc._calculate_component_scores(
            {"crime_index": 5.0, "accident_rate": 4.0, "socioeconomic_level": 6.0, "weather": "Stormy"})
        assert comps["crime_index"] == pytest.approx(0.5)
        assert comps["accident_rate"] == pytest.approx(0.4)
        assert comps["socioeconomic_level"] == pytest.approx(5 / 9)  # (11 - 6) / 9
        assert comps["weather"] == pytest.approx(0.9)

    def test_higher_socioeconomic_level_means_lower_risk(self, proc):
        low = proc.process_risk_data(data(socioeconomic_level=2))
        high = proc.process_risk_data(data(socioeconomic_level=9))
        assert low["risk_score"] > high["risk_score"]

    @pytest.mark.xfail(
        reason="Real bug: socioeconomic component is (11 - x) / 9, so socioeconomic_level=1 "
               "gives 1.11 (>1) and level 10 gives 0.11 instead of 0; the documented 0-1 "
               "normalisation is exceeded at the low end.",
        strict=True,
    )
    def test_socioeconomic_component_stays_within_unit_interval(self, proc):
        for level in range(1, 11):
            comps = proc._calculate_component_scores(
                {"crime_index": 5.0, "accident_rate": 4.0,
                 "socioeconomic_level": float(level), "weather": "Clear"})
            assert 0.0 <= comps["socioeconomic_level"] <= 1.0


class TestScoring:
    def test_baseline_score_no_rules(self, proc):
        r = proc.process_risk_data(data())
        expected = (0.5 * 0.30 + 0.4 * 0.25 + (5 / 9) * 0.25 + 0.1 * 0.20) * 100
        assert r["risk_score"] == pytest.approx(round(expected, 2))
        assert r["crime_index_component"] == 50.0
        assert r["accident_rate_component"] == 40.0
        assert r["socioeconomic_level_component"] == pytest.approx(55.56)
        assert r["weather_component"] == 10.0
        assert "city" not in r

    def test_city_is_passed_through(self, proc):
        assert proc.process_risk_data(data(city=" Oslo "))["city"] == "Oslo"

    def test_high_crime_severe_weather_rule_amplifies(self, proc):
        r = proc.process_risk_data(data(crime_index=8, accident_rate=6, socioeconomic_level=5, weather="Stormy"))
        base = 0.8 * 0.30 + 0.6 * 0.25 + (6 / 9) * 0.25 + 0.9 * 0.20
        assert r["risk_score"] == pytest.approx(round(base * 1.15 * 100, 2))

    def test_low_crime_clear_weather_rule_reduces(self, proc):
        r = proc.process_risk_data(data(crime_index=3, accident_rate=2, socioeconomic_level=8, weather="Clear"))
        base = 0.3 * 0.30 + 0.2 * 0.25 + (3 / 9) * 0.25 + 0.1 * 0.20
        assert r["risk_score"] == pytest.approx(round(base * 0.9 * 100, 2))

    def test_rule_threshold_is_strict(self, proc):
        # crime_index == 7 does not satisfy ">7"; crime_index == 4 does not satisfy "<4"
        at7 = proc.process_risk_data(data(crime_index=7, weather="Stormy"))
        just_over = proc.process_risk_data(data(crime_index=7.01, weather="Stormy"))
        assert just_over["risk_score"] > at7["risk_score"] * 1.10
        at4 = proc.process_risk_data(data(crime_index=4, weather="Clear"))
        base4 = 0.4 * 0.30 + 0.4 * 0.25 + (5 / 9) * 0.25 + 0.1 * 0.20
        assert at4["risk_score"] == pytest.approx(round(base4 * 100, 2))

    def test_score_is_clamped_to_100(self, proc):
        r = proc.process_risk_data(data(crime_index=10, accident_rate=10, socioeconomic_level=1, weather="Extreme"))
        assert r["risk_score"] == 100.0
        assert all(0 <= r[k] <= 100 for k in r if k.endswith("_component"))

    def test_score_lower_bound(self, proc):
        r = proc.process_risk_data(data(crime_index=0, accident_rate=0, socioeconomic_level=10, weather="Clear"))
        assert 0 <= r["risk_score"] < 15

    def test_custom_weights_and_rules(self):
        p = RiskProcessor(weights={"crime_index": 1.0, "accident_rate": 0.0,
                                   "socioeconomic_level": 0.0, "weather": 0.0},
                          amplification_rules=[{"conditions": {"weather": ["Rainy"]}, "multiplier": 2.0}],
                          noise_level=0.0)
        assert p.process_risk_data(data(crime_index=2, weather="Clear"))["risk_score"] == 20.0
        assert p.process_risk_data(data(crime_index=2, weather="Rainy"))["risk_score"] == 40.0

    def test_invalid_input_raises_validation_error(self, proc):
        with pytest.raises(ValidationError):
            proc.process_risk_data(data(weather="Foggy"))
        with pytest.raises(ValidationError):
            proc.process_risk_data({})


class TestRuleEvaluation:
    @pytest.mark.parametrize("cond,value,expected", [
        (">7", 8, True), (">7", 7, False), ("<3", 2, True), ("<3", 3, False),
        ("=5", 5, True), ("=5", 6, False), (5, 5, True), (5, 4, False),
        ({"A", "B"}, "A", True), ({"A", "B"}, "C", False), (["A"], "A", True),
    ])
    def test_conditions(self, proc, cond, value, expected):
        assert proc._evaluate_rule_conditions({"x": cond}, {"x": value}) is expected

    def test_missing_field_fails_rule(self, proc):
        assert proc._evaluate_rule_conditions({"x": ">1"}, {"y": 5}) is False

    def test_all_conditions_must_hold(self, proc):
        conds = {"a": ">1", "b": {"Z"}}
        assert proc._evaluate_rule_conditions(conds, {"a": 2, "b": "Z"}) is True
        assert proc._evaluate_rule_conditions(conds, {"a": 2, "b": "Y"}) is False

    def test_malformed_string_condition_is_ignored(self, proc):
        assert proc._evaluate_rule_conditions({"x": ">abc"}, {"x": 1}) is True
        assert proc._evaluate_rule_conditions({"x": ">"}, {"x": 1}) is True


class TestNoiseAndConfig:
    def test_noise_zero_is_deterministic(self, proc):
        assert proc._add_statistical_noise(0.42) == 0.42
        assert proc.process_risk_data(data()) == proc.process_risk_data(data())

    def test_noise_stays_in_band_and_clamped(self):
        p = RiskProcessor(noise_level=0.05)
        for _ in range(200):
            s = p._add_statistical_noise(0.5)
            assert 0.45 <= s <= 0.55
            assert 0.0 <= p._add_statistical_noise(0.99) <= 1.0
            assert 0.0 <= p._add_statistical_noise(0.01) <= 1.0

    def test_deterministic_mode_toggle(self):
        p = RiskProcessor(noise_level=0.2)
        p.set_deterministic_mode(True)
        assert p.noise_level == 0.0
        p.set_deterministic_mode(False)
        assert p.noise_level == 0.2

    def test_info(self, proc):
        info = proc.get_processor_info()
        assert info["weights"] == DEFAULT_WEIGHTS
        assert info["rules_count"] == 2
        assert info["output_scale"] == 100
        assert "Stormy" in info["weather_categories"]

    def test_weights_not_summing_to_one_warns(self, capsys):
        RiskProcessor(weights={"crime_index": 0.5, "accident_rate": 0.5,
                               "socioeconomic_level": 0.5, "weather": 0.5})
        assert "not 1.0" in capsys.readouterr().out
