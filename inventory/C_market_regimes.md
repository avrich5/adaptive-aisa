# C — Market Regime Classification: base-states Service

**Source path:** `~/wbprd_macbook/base-states/`
**Date of inventory:** 2026-06-05
**Branch:** dev @ 4ff792d

---

## 1. all_regimes.parquet

**Location on MacBook:** Not present. Only `data/realtime_output/live_state.json` and `data/realtime_output/narrative_cache.json` exist locally. The `data/parquet/` and `data/pipeline_output/` directories are git-ignored and not cloned to MacBook.

**Where it is generated:** `pipeline/output.py → save_combined_parquet()` (Block 5 of the batch pipeline). Written to `data/pipeline_output/{market}/all_regimes.parquet` when `python -m pipeline.main` runs on skufs.

Two separate files: `data/pipeline_output/binance/all_regimes.parquet` and `data/pipeline_output/whitebit/all_regimes.parquet`.

**Schema (reconstructed from code):**

| Column | Source |
|--------|--------|
| `open`, `high`, `low`, `close`, `volume` | Raw OHLCV |
| `regime` | Classification label (e.g. `R1_BULL_TREND`) |
| `asset` | Symbol string (e.g. `BTCUSDT`, `BTC_USDT`) |
| `ema_slope_pctl` | EMA(50) slope percentile |
| `adx_pctl` | ADX(14) percentile |
| `adx_raw` | Raw ADX value |
| `price_vs_ema200` | close / EMA(200) ratio |
| `hh_hl_score` | Higher-highs/higher-lows fraction (0.0–1.0) |
| `atr_pctl` | ATR(14) percentile |
| `atr_pct` | ATR as % of price |
| `bb_width_pctl` | Bollinger Band width percentile |
| `realized_vol_pctl` | 20-day realized vol percentile |
| `volume_zscore` | Volume z-score vs. 60-day mean |
| `volume_pctl` | Volume percentile |
| `volume_trend` | Short MA (20d) / Long MA (60d) ratio |
| `return_5d`, `return_20d`, `return_60d` | Return over N days |
| `return_5d_pctl`, `return_20d_pctl` | Percentile of returns |
| `drawdown_from_high` | % from 252-day rolling high (negative) |
| `rally_from_low` | % from 252-day rolling low (positive) |
| `range_position` | Price position in 60-day H/L range (0–1) |
| `hl_range_pctl` | Intraday H-L spread percentile |
| `body_ratio` | Candle body / total range |

**Index:** Date (daily, one row per asset per day).

**Timeframe:** Daily candles. History: `YEARS_HISTORY = 5`. First 252 days per asset are `UNCLASSIFIED` (warmup). Classification begins at day 253.

**Date range:** [UNKNOWN — requires clarification: file not on MacBook; run `python3 -c "import pandas as pd; df=pd.read_parquet('data/pipeline_output/binance/all_regimes.parquet'); print(df.index.min(), df.index.max())"` on skufs]

---

## 2. Regime Detection Algorithm

**Type:** Rule-based deterministic. Not HMM, not clustering, not ML.

**Primary file:** `pipeline/state_rules.py`

**Primary function:** `classify_regime(row: pd.Series, thresholds: dict) -> str`

The algorithm is a fixed-priority cascade of boolean rules. Each daily feature row is evaluated against rules in a fixed order; the first matching rule returns its regime code. No model training, no transition matrix inference — all conditions are explicit threshold comparisons on percentile-normalized features.

**Supporting function (full timeseries):** `classify_timeseries(features_df, thresholds) -> pd.Series` — applies `classify_regime` row by row starting from `WARMUP_DAYS=252`, then runs two post-processing passes.

**Optimized variant:** `classify_timeseries_optimized()` — same base `classify_regime()` but adds hysteresis (regime sticky within ±5 percentile of threshold) and expanded regime groups for R12 insertion. Fewer flickers, fewer R12 days.

**Feature computation:** `pipeline/features.py → compute_features(df)` — ~20 rolling indicators, all percentile-normalized vs. a 252-day window. No look-ahead bias.

---

## 3. Exact Regime List

Defined in `pipeline/config.py → REGIMES` dict. Priority cascade in `classify_regime()` determines evaluation order.

| Code | Full Name | Key Conditions | Priority |
|------|-----------|----------------|----------|
| R1 | R1_BULL_TREND | price > EMA200, EMA slope > 55th pctl; confirmed by ADX > 35th pctl OR HH/HL score > 0.55 | 9 (low) |
| R2 | R2_BEAR_TREND | price < EMA200, EMA slope < 45th pctl; confirmed by ADX > 35th pctl OR HH/HL score < 0.45 | 10 (low) |
| R3 | R3_RANGE | ADX < 65th pctl AND BB width < 65th pctl; also unconditional fallback | 11 (default) |
| R4 | R4_HIGH_VOLATILITY | ATR > 75th pctl AND ADX < 65th pctl (no strong trend) | 4 |
| R5 | R5_LOW_VOLATILITY | ATR < 25th pctl AND BB width < 30th pctl | 5 |
| R6 | R6_ACCUMULATION | drawdown < −25%, price < EMA200, rising volume (short MA > long MA) | 6 |
| R7 | R7_DISTRIBUTION | drawdown > −10%, range position > 0.7, declining volume, slope < 55th pctl, 60d return > 10% | 7 |
| R8 | R8_CAPITULATION | drawdown < −30%, ATR > 95th pctl, volume z-score > 2.0, 5d return pctl < 5th | 1 (highest) |
| R9 | R9_SPECULATIVE_MANIA | rally > 100% from low, 5d return pctl > 95th, ATR > 75th pctl, volume z-score > 2.0 | 3 |
| R10 | R10_LIQUIDITY_STRESS | H-L range pctl > 95th, ATR > 75th pctl, volume pctl < 25th | 2 |
| R11 | R11_STRUCTURAL_TRANSITION | price within ±3% of EMA200, ADX 35–65th pctl, ATR < 75th pctl, slope 35–65th pctl | 8 |
| R12 | R12_REGIME_TRANSITION | Post-processing marker — inserted at group boundaries during `_mark_transitions()` | N/A — post-process only |

**Data sufficiency** (from `config.py → DATA_SUFFICIENCY`): R1–R8, R11, R12 = `"full"`; R9, R10 = `"proxy"` (rare events, thin sample).

**Composite pseudo-regimes** (from `composite_state.py`): `MIXED` (no single regime reaches 40% weighted consensus), `UNCLASSIFIED` (warmup period).

---

## 4. Per-Asset or Global

**Both.** Two levels:

**Per-asset (primary classification):** `classify_regime()` runs independently on each asset's feature row. Each of the 7 assets (BTC, ETH, BNB, SOL, XRP, ADA, DOGE) receives its own daily R1–R12 label. This is the output stored in `all_regimes.parquet`.

**Global composite (derived):** `pipeline/composite_state.py → compute_composite_state()` aggregates per-asset labels into a single market-wide state using weighted consensus. Weights: BTC=0.35, ETH=0.20, BNB/SOL/XRP=0.10, ADA=0.08, DOGE=0.07. If no single regime reaches 40% weighted share (`min_consensus_strength = 0.40`), composite label is `MIXED`. The composite state includes breadth metrics (`bull_pct`, `bear_pct`, `neutral_pct`, `crisis_pct`) and divergence detection (BTC leads / alts lead / sector split).

The API exposes both: per-asset via `GET /api/asset/{symbol}` and composite via `GET /api/live`.

---

## 5. Detection Latency

**Classification is on daily (closed) candles only.** `INTERVAL = "1d"` and `LOOKBACK_PERCENTILE = 252` — all features require full-day OHLCV bars.

**Intraday state is not classified.** The live fetcher (`app/core/live_fetcher.py`) fetches the current daily candle, which may be open (in progress). The snapshot includes `is_candle_closed: bool` and `preliminary_warning: bool` flags.

**Behavior on open candle:** `get_live_snapshot()` appends the live (potentially open) candle to the historical parquet data and runs the full classification pipeline. The resulting label for the current day reflects intraday data up to the fetch time. The `preliminary_warning: true` flag signals this. `live_state.json` confirms: snapshot from 2026-02-25T13:33:06Z has `"is_candle_closed": false` and `"preliminary_warning": true`.

**Final determination:** Available only after daily candle close (UTC midnight). The daily pipeline cron runs at `PIPELINE_TRIGGER_HOUR:PIPELINE_TRIGGER_MINUTE UTC` (default 00:05 UTC, configurable via env).

**Refresh interval:** Configurable via `UPDATE_INTERVAL_MINUTES` env var. Default — [UNKNOWN — requires clarification: set in `.env` on skufs, not visible in code without `.env` file]

---

## 6. Transition Matrix

**Pre-computed, runtime in-memory. No standalone file on disk.**

**How it is built:**

File: `app/core/transition_probs.py → build_markov_matrix(parquet_path)`

On server startup (lifespan), `build_markov_matrix(output_dir_for(market) / "all_regimes.parquet")` is called for each enabled market. The function reads the parquet, iterates every asset's regime series, and counts day-over-day transitions between any two R1–R12 codes. Each row is normalized to probabilities (row sums to 1.0). If a regime has zero outgoing transitions (never seen in data), a uniform 1/12 distribution is assigned.

The matrix is stored in `MARKET_STATES[market]["markov"]` — in-process dict-of-dicts, not persisted to disk.

**Additionally:** `pipeline/validation.py → compute_transition_matrix(labels)` computes a raw transition count matrix (not normalized) for each per-asset label series during the batch pipeline's Block 4 validation step. This is logged in `regime_summary.json` via `full_validation()` — a validation artifact, not the runtime matrix.

**How the matrix is used:**

`transition_probs.py → get_transition_distribution()` blends two signals:
- 70% (`TRANSITION_ALPHA = 0.7`): historical Markov row for the current composite regime
- 30%: proximity scores (soft feature-based closeness to each regime, from `app/core/proximity.py`)

Result: `distribution` dict of `{regime: probability}` for all 12 regimes, consumed by `GET /api/transition`.

**Matrix is rebuilt** after each daily pipeline run via `run_daily_pipeline()` in `app/server.py`.
