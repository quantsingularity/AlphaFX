"""
AlphaFX Django Test Suite
45+ tests covering pricing, risk, technical, and all API endpoints.
"""

import math

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

# ─── Pricing engine tests ──────────────────────────────────────────────────────


class TestSpotRates(TestCase):

    def test_known_pair_returns_correct_rate(self):
        from apps.core.pricing import FALLBACK_RATES, get_spot_rate

        assert get_spot_rate("EURUSD") == FALLBACK_RATES["EURUSD"]

    def test_inverse_lookup(self):
        from apps.core.pricing import FALLBACK_RATES, get_spot_rate

        inv = get_spot_rate("USDEUR")
        assert abs(inv - 1 / FALLBACK_RATES["EURUSD"]) < 1e-8

    def test_jpy_pair_rate_positive(self):
        from apps.core.pricing import get_spot_rate

        assert get_spot_rate("USDJPY") > 100

    def test_all_major_pairs_positive(self):
        from apps.core.pricing import MAJOR_PAIRS, get_spot_rate

        for pair in MAJOR_PAIRS:
            assert get_spot_rate(pair) > 0, f"{pair} rate not positive"

    def test_pip_size_jpy(self):
        from apps.core.pricing import pip_size

        assert pip_size("USDJPY") == 0.01

    def test_pip_size_standard(self):
        from apps.core.pricing import pip_size

        assert pip_size("EURUSD") == 0.0001

    def test_pip_value_usd_quote(self):
        from apps.core.pricing import pip_value

        pv = pip_value("EURUSD", 100_000, 1.08)
        assert abs(pv - 10.0) < 0.01

    def test_pip_value_usd_base(self):
        from apps.core.pricing import pip_value

        pv = pip_value("USDJPY", 100_000, 154.0)
        assert pv > 0


class TestCrossRates(TestCase):

    def test_same_currency_returns_one(self):
        from apps.core.pricing import compute_cross_rate

        assert compute_cross_rate("USD", "USD") == 1.0

    def test_direct_pair_consistency(self):
        from apps.core.pricing import FALLBACK_RATES, compute_cross_rate

        rate = compute_cross_rate("EUR", "USD")
        assert abs(rate - FALLBACK_RATES["EURUSD"]) < 1e-4

    def test_triangulation_produces_positive_rate(self):
        from apps.core.pricing import compute_cross_rate

        rate = compute_cross_rate("GBP", "JPY")
        assert rate > 0


class TestForwardRates(TestCase):

    def test_positive_carry_forward_above_spot(self):
        from apps.core.pricing import compute_forward_rate

        fwd, pts = compute_forward_rate(1.08, 0.001, 0.05, 90)
        assert fwd > 1.08

    def test_negative_carry_forward_below_spot(self):
        from apps.core.pricing import compute_forward_rate

        fwd, pts = compute_forward_rate(1.08, 0.05, 0.001, 90)
        assert fwd < 1.08

    def test_flat_carry_forward_equals_spot(self):
        from apps.core.pricing import compute_forward_rate

        fwd, pts = compute_forward_rate(1.08, 0.05, 0.05, 90)
        assert abs(fwd - 1.08) < 1e-8

    def test_longer_tenor_larger_deviation(self):
        from apps.core.pricing import compute_forward_rate

        _, pts_30 = compute_forward_rate(1.08, 0.001, 0.05, 30)
        _, pts_90 = compute_forward_rate(1.08, 0.001, 0.05, 90)
        assert abs(pts_90) > abs(pts_30)

    def test_forward_points_sign(self):
        from apps.core.pricing import compute_forward_rate

        _, pts = compute_forward_rate(1.08, 0.001, 0.05, 90)
        assert pts > 0  # quote rate > base rate → forward premium


class TestGarmanKohlhagen(TestCase):

    def setUp(self):
        from apps.core.pricing import OptionRequest

        self.base_req = OptionRequest(
            base="EUR",
            quote="USD",
            spot=1.08,
            strike=1.08,
            tenor_days=30,
            volatility=0.08,
            base_rate=0.04,
            quote_rate=0.05,
            option_type="call",
        )

    def test_call_price_positive(self):
        from apps.core.pricing import garman_kohlhagen

        result = garman_kohlhagen(self.base_req)
        assert result.price > 0

    def test_put_price_positive(self):
        from apps.core.pricing import OptionRequest, garman_kohlhagen

        req = OptionRequest(**{**self.base_req.__dict__, "option_type": "put"})
        result = garman_kohlhagen(req)
        assert result.price > 0

    def test_call_delta_in_range(self):
        from apps.core.pricing import garman_kohlhagen

        result = garman_kohlhagen(self.base_req)
        assert 0 < result.delta < 1

    def test_put_delta_in_range(self):
        from apps.core.pricing import OptionRequest, garman_kohlhagen

        req = OptionRequest(**{**self.base_req.__dict__, "option_type": "put"})
        result = garman_kohlhagen(req)
        assert -1 < result.delta < 0

    def test_gamma_positive(self):
        from apps.core.pricing import garman_kohlhagen

        result = garman_kohlhagen(self.base_req)
        assert result.gamma > 0

    def test_vega_positive(self):
        from apps.core.pricing import garman_kohlhagen

        result = garman_kohlhagen(self.base_req)
        assert result.vega > 0

    def test_put_call_parity(self):
        """C - P = S*exp(-r_f*T) - K*exp(-r_d*T)"""
        from apps.core.pricing import OptionRequest, garman_kohlhagen

        req_c = self.base_req
        req_p = OptionRequest(**{**req_c.__dict__, "option_type": "put"})
        C = garman_kohlhagen(req_c).price
        P = garman_kohlhagen(req_p).price
        T = req_c.tenor_days / 365.0
        parity = req_c.spot * math.exp(-req_c.base_rate * T) - req_c.strike * math.exp(
            -req_c.quote_rate * T
        )
        assert abs((C - P) - parity) < 5e-5

    def test_deep_itm_call_high_delta(self):
        from apps.core.pricing import OptionRequest, garman_kohlhagen

        req = OptionRequest(**{**self.base_req.__dict__, "spot": 1.20, "strike": 1.00})
        result = garman_kohlhagen(req)
        assert result.delta > 0.9

    def test_deep_otm_call_low_delta(self):
        from apps.core.pricing import OptionRequest, garman_kohlhagen

        req = OptionRequest(**{**self.base_req.__dict__, "spot": 1.00, "strike": 1.30})
        result = garman_kohlhagen(req)
        assert result.delta < 0.1

    def test_time_value_non_negative(self):
        from apps.core.pricing import garman_kohlhagen

        result = garman_kohlhagen(self.base_req)
        assert result.time_value >= 0

    def test_higher_vol_higher_price(self):
        from apps.core.pricing import OptionRequest, garman_kohlhagen

        req_lo = OptionRequest(**{**self.base_req.__dict__, "volatility": 0.05})
        req_hi = OptionRequest(**{**self.base_req.__dict__, "volatility": 0.20})
        assert garman_kohlhagen(req_hi).price > garman_kohlhagen(req_lo).price


class TestCarryTrade(TestCase):

    def test_returns_list(self):
        from apps.core.pricing import carry_opportunities

        result = carry_opportunities()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_sorted_descending(self):
        from apps.core.pricing import carry_opportunities

        result = carry_opportunities()
        carries = [r["carry_rate_bps"] for r in result]
        assert carries == sorted(carries, reverse=True)

    def test_min_carry_filter(self):
        from apps.core.pricing import carry_opportunities

        result = carry_opportunities(min_carry_bps=500)
        assert all(r["carry_rate_bps"] >= 500 for r in result)

    def test_carry_to_vol_ratio_present(self):
        from apps.core.pricing import carry_opportunities

        result = carry_opportunities()
        assert all("carry_to_vol_ratio" in r for r in result)

    def test_high_yielder_in_top(self):
        from apps.core.pricing import carry_opportunities

        result = carry_opportunities()
        # TRY has highest carry (50% rate)
        top_pairs = [r["pair"] for r in result[:5]]
        assert any("TRY" in p for p in top_pairs)


class TestVolSurface(TestCase):

    def test_surface_has_all_tenors(self):
        from apps.core.pricing import implied_volatility_surface

        surf = implied_volatility_surface("EURUSD")
        assert "1D" in surf["surface"]
        assert "365D" in surf["surface"]

    def test_atm_positive(self):
        from apps.core.pricing import implied_volatility_surface

        surf = implied_volatility_surface("EURUSD")
        assert surf["surface"]["30D"]["50"] > 0

    def test_smile_wings_higher_than_atm(self):
        from apps.core.pricing import implied_volatility_surface

        surf = implied_volatility_surface("EURUSD")
        atm = surf["surface"]["30D"]["50"]
        wing = surf["surface"]["30D"]["10"]
        assert wing >= atm


# ─── Technical analysis tests ─────────────────────────────────────────────────


class TestTechnicalAnalysis(TestCase):

    def test_signal_in_valid_set(self):
        from apps.core.technical import full_analysis

        result = full_analysis("EURUSD", 252)
        valid = {"STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG_BEARISH"}
        assert result["signal"] in valid

    def test_rsi_in_range(self):
        from apps.core.technical import full_analysis

        result = full_analysis("EURUSD", 252)
        assert 0 <= result["indicators"]["rsi_14"] <= 100

    def test_stoch_in_range(self):
        from apps.core.technical import full_analysis

        result = full_analysis("GBPUSD", 100)
        assert 0 <= result["indicators"]["stoch_k"] <= 100

    def test_williams_r_in_range(self):
        from apps.core.technical import full_analysis

        result = full_analysis("USDJPY", 100)
        assert -100 <= result["indicators"]["williams_r"] <= 0

    def test_all_indicators_present(self):
        from apps.core.technical import full_analysis

        result = full_analysis("EURUSD", 100)
        expected = [
            "rsi_14",
            "macd",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_mid",
            "bb_lower",
            "atr_14",
            "ema_20",
            "ema_50",
            "ema_200",
            "stoch_k",
            "stoch_d",
            "williams_r",
            "vwap",
            "ichimoku_tenkan",
            "ichimoku_kijun",
        ]
        for key in expected:
            assert key in result["indicators"], f"Missing indicator: {key}"

    def test_pivot_points_present(self):
        from apps.core.technical import full_analysis

        result = full_analysis("EURUSD", 100)
        for key in ("pivot", "R1", "R2", "S1", "S2"):
            assert key in result["pivot_points"]

    def test_ohlcv_correct_length(self):
        from apps.core.technical import full_analysis

        result = full_analysis("EURUSD", 252)
        assert len(result["ohlcv"]) == 100

    def test_correlation_matrix_shape(self):
        from apps.core.technical import correlation_matrix

        pairs = ["EURUSD", "GBPUSD", "USDJPY"]
        result = correlation_matrix(pairs, n=60)
        assert len(result["matrix"]) == 3
        assert len(result["matrix"][0]) == 3

    def test_correlation_diagonal_is_one(self):
        from apps.core.technical import correlation_matrix

        pairs = ["EURUSD", "GBPUSD"]
        result = correlation_matrix(pairs, n=60)
        assert abs(result["matrix"][0][0] - 1.0) < 1e-6
        assert abs(result["matrix"][1][1] - 1.0) < 1e-6


# ─── Risk engine tests ─────────────────────────────────────────────────────────


class TestRiskEngine(TestCase):

    def _sample_positions(self):
        return [
            {"pair": "EURUSD", "side": "buy", "notional": 100_000, "entry_rate": 1.08},
            {"pair": "GBPUSD", "side": "sell", "notional": 50_000, "entry_rate": 1.26},
        ]

    def test_position_pnl_buy_profit(self):
        from apps.core.risk import position_pnl

        pnl = position_pnl("EURUSD", "buy", 100_000, 1.08, 1.09)
        assert pnl > 0

    def test_position_pnl_sell_profit(self):
        from apps.core.risk import position_pnl

        pnl = position_pnl("EURUSD", "sell", 100_000, 1.09, 1.08)
        assert pnl > 0

    def test_var_positive(self):
        from apps.core.risk import portfolio_var

        result = portfolio_var(self._sample_positions())
        assert result["var_1d"] >= 0
        assert result["var_10d"] >= result["var_1d"]

    def test_empty_portfolio_var_zero(self):
        from apps.core.risk import portfolio_var

        result = portfolio_var([])
        assert result["var_1d"] == 0.0

    def test_expected_shortfall_gte_var(self):
        from apps.core.risk import portfolio_var

        result = portfolio_var(self._sample_positions())
        assert result["expected_shortfall"] >= result["var_1d"]

    def test_net_exposure_structure(self):
        from apps.core.risk import net_currency_exposure

        exp = net_currency_exposure(self._sample_positions())
        assert "EUR" in exp
        assert "USD" in exp

    def test_hhi_single_position(self):
        from apps.core.risk import herfindahl_index

        pos = [{"notional": 100_000}]
        assert herfindahl_index(pos) == 1.0

    def test_hhi_equal_positions(self):
        from apps.core.risk import herfindahl_index

        pos = [{"notional": 50_000}, {"notional": 50_000}]
        assert abs(herfindahl_index(pos) - 0.5) < 1e-9

    def test_scenarios_returns_ten(self):
        from apps.core.risk import run_fx_scenarios

        results = run_fx_scenarios(self._sample_positions(), 100_000)
        assert len(results) == 10

    def test_scenario_equity_changes(self):
        from apps.core.risk import run_fx_scenarios

        results = run_fx_scenarios(self._sample_positions(), 100_000)
        # At least some scenarios should show non-zero P&L
        pnls = [r["pnl"] for r in results]
        assert any(abs(p) > 0 for p in pnls)


# ─── API endpoint tests ────────────────────────────────────────────────────────


class TestRatesAPI(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_major_pairs_returns_list(self):
        resp = self.client.get("/api/v1/rates/")
        assert resp.status_code == status.HTTP_200_OK
        assert "pairs" in resp.data
        assert len(resp.data["pairs"]) > 0

    def test_spot_rate_eurusd(self):
        resp = self.client.get("/api/v1/rates/spot/EURUSD/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["pair"] == "EURUSD"
        assert resp.data["bid"] < resp.data["ask"]

    def test_spot_rate_invalid_pair(self):
        resp = self.client.get("/api/v1/rates/spot/INVALID/")
        assert resp.status_code in (400, 404)

    def test_forward_rate_post(self):
        resp = self.client.post(
            "/api/v1/rates/forward/",
            {"base": "EUR", "quote": "USD", "tenor_days": 30},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "forward_rate" in resp.data

    def test_cross_rate_post(self):
        resp = self.client.post(
            "/api/v1/rates/cross/", {"base": "GBP", "quote": "JPY"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["rate"] > 0

    def test_fx_option_post(self):
        resp = self.client.post(
            "/api/v1/rates/option/",
            {
                "base": "EUR",
                "quote": "USD",
                "spot": 1.08,
                "strike": 1.08,
                "tenor_days": 30,
                "volatility": 0.08,
                "base_rate": 0.04,
                "quote_rate": 0.05,
                "option_type": "call",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "greeks" in resp.data
        assert resp.data["price"] > 0

    def test_vol_surface(self):
        resp = self.client.get("/api/v1/rates/option/vol-surface/EURUSD/")
        assert resp.status_code == status.HTTP_200_OK
        assert "surface" in resp.data

    def test_risk_reversal(self):
        resp = self.client.get("/api/v1/rates/option/risk-reversal/EURUSD/")
        assert resp.status_code == status.HTTP_200_OK
        assert "rr_25d_30d" in resp.data

    def test_carry_screen(self):
        resp = self.client.get("/api/v1/rates/carry/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["opportunities"]) > 0

    def test_interest_rates(self):
        resp = self.client.get("/api/v1/rates/interest-rates/")
        assert resp.status_code == status.HTTP_200_OK
        assert "USD" in resp.data["rates"]

    def test_economic_calendar(self):
        resp = self.client.get("/api/v1/rates/calendar/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["events"]) > 0

    def test_pip_value_endpoint(self):
        resp = self.client.get("/api/v1/rates/pip-value/EURUSD/?notional=100000")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["pip_value_usd"] > 0


class TestPortfolioAPI(TestCase):

    def setUp(self):
        self.client = APIClient()

    def _create_portfolio(self, name="Test Portfolio"):
        resp = self.client.post(
            "/api/v1/portfolios/",
            {
                "name": name,
                "base_currency": "USD",
                "initial_balance": 100000,
            },
            format="json",
        )
        return resp

    def test_create_portfolio(self):
        resp = self._create_portfolio()
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Test Portfolio"

    def test_list_portfolios(self):
        self._create_portfolio("Port A")
        self._create_portfolio("Port B")
        resp = self.client.get("/api/v1/portfolios/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 2

    def test_get_portfolio_detail(self):
        create_resp = self._create_portfolio()
        pid = create_resp.data["id"]
        resp = self.client.get(f"/api/v1/portfolios/{pid}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["id"] == pid

    def test_delete_portfolio(self):
        create_resp = self._create_portfolio()
        pid = create_resp.data["id"]
        resp = self.client.delete(f"/api/v1/portfolios/{pid}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_open_position(self):
        create_resp = self._create_portfolio()
        pid = create_resp.data["id"]
        resp = self.client.post(
            f"/api/v1/portfolios/{pid}/positions/",
            {
                "pair": "EURUSD",
                "side": "buy",
                "notional": 50000,
                "entry_rate": 1.0850,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "unrealized_pnl" in resp.data

    def test_list_positions(self):
        create_resp = self._create_portfolio()
        pid = create_resp.data["id"]
        self.client.post(
            f"/api/v1/portfolios/{pid}/positions/",
            {
                "pair": "GBPUSD",
                "side": "sell",
                "notional": 25000,
                "entry_rate": 1.2600,
            },
            format="json",
        )
        resp = self.client.get(f"/api/v1/portfolios/{pid}/positions/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1

    def test_portfolio_risk(self):
        create_resp = self._create_portfolio()
        pid = create_resp.data["id"]
        self.client.post(
            f"/api/v1/portfolios/{pid}/positions/",
            {
                "pair": "EURUSD",
                "side": "buy",
                "notional": 100000,
                "entry_rate": 1.08,
            },
            format="json",
        )
        resp = self.client.get(f"/api/v1/portfolios/{pid}/risk/")
        assert resp.status_code == status.HTTP_200_OK
        assert "var_1d" in resp.data

    def test_portfolio_scenarios(self):
        create_resp = self._create_portfolio()
        pid = create_resp.data["id"]
        self.client.post(
            f"/api/v1/portfolios/{pid}/positions/",
            {
                "pair": "EURUSD",
                "side": "buy",
                "notional": 100000,
                "entry_rate": 1.08,
            },
            format="json",
        )
        resp = self.client.post(f"/api/v1/portfolios/{pid}/scenarios/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["scenarios"]) == 10


class TestAnalyticsAPI(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_position_size(self):
        resp = self.client.post(
            "/api/v1/analytics/position-size/",
            {
                "account_balance": 10000,
                "risk_pct": 1.0,
                "stop_loss_pips": 50,
                "pair": "EURUSD",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["recommended_lots"] > 0

    def test_risk_reward(self):
        resp = self.client.post(
            "/api/v1/analytics/risk-reward/",
            {
                "entry": 1.0850,
                "stop_loss": 1.0800,
                "take_profit": 1.0950,
                "pair": "EURUSD",
                "side": "buy",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["risk_reward_ratio"] == 2.0

    def test_swap_rates(self):
        resp = self.client.get("/api/v1/analytics/swap-rates/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["swap_rates"]) > 0

    def test_ppp_analysis(self):
        resp = self.client.get("/api/v1/analytics/purchasing-power-parity/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["ppp_analysis"]) > 0

    def test_sabr_smile(self):
        resp = self.client.post(
            "/api/v1/analytics/sabr-smile/",
            {
                "pair": "EURUSD",
                "forward": 1.08,
                "tenor_days": 30,
                "atm_vol": 0.08,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "smile" in resp.data
        assert len(resp.data["smile"]) == 5

    def test_strategy_builder_straddle(self):
        resp = self.client.post(
            "/api/v1/analytics/strategy-builder/",
            {
                "pair": "EURUSD",
                "volatility": 0.08,
                "legs": [
                    {
                        "option_type": "call",
                        "strike": 1.08,
                        "tenor_days": 30,
                        "notional": 1000000,
                        "direction": "long",
                    },
                    {
                        "option_type": "put",
                        "strike": 1.08,
                        "tenor_days": 30,
                        "notional": 1000000,
                        "direction": "long",
                    },
                ],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["strategy_name"] == "Long Straddle"
        assert len(resp.data["payoff_at_expiry"]) == 21


class TestTechnicalAPI(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_technical_analysis_pair(self):
        resp = self.client.get("/api/v1/technical/EURUSD/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["pair"] == "EURUSD"
        assert "indicators" in resp.data

    def test_technical_scan(self):
        resp = self.client.get("/api/v1/technical/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] > 0

    def test_correlation_matrix(self):
        resp = self.client.get(
            "/api/v1/technical/correlation/?pairs=EURUSD,GBPUSD,USDJPY"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["matrix"]) == 3

    def test_support_resistance(self):
        resp = self.client.get("/api/v1/technical/EURUSD/support-resistance/")
        assert resp.status_code == status.HTTP_200_OK
        assert "resistance" in resp.data
        assert "support" in resp.data

    def test_fibonacci(self):
        resp = self.client.get("/api/v1/technical/GBPUSD/fibonacci/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["retracements"]) == 7

    def test_volatility_analysis(self):
        resp = self.client.get("/api/v1/technical/EURUSD/volatility/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["current_hv_21d_pct"] > 0


class TestHealthEndpoints(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_root_returns_name(self):
        resp = self.client.get("/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "AlphaFX"

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert "status" in resp.data
