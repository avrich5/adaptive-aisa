# G — How "BY MARKET REGIME" table is built in Detail view

Investigated 2026-06-05 after `dev.dashboard_strategy_regimes` returned zero rows.

## Conclusion

The per-regime breakdown table in Detail view is **computed on-the-fly per request**, not cached. There is no programmatic Strategy × Regime matrix anywhere in the system today.

## Source path

Frontend: `frontend/src/pages/strategy-dashboard/PageDetail.tsx`, `loadRunData` callback:

```js
api.get(`/backtest-run/${btRunId}/regime-performance`)
  .then(d => { if (d) setBtRegime(d as Record<string, unknown>); })
```

Backend: `backend/app/routers/backtests.py`, endpoint `GET /backtest-run/{bt_run_id}/regime-performance`.

## What the endpoint does (per request)

For each detail-page visit, for each strategy:

1. Load `backtest_runs` row by UUID (gets symbol, market, config).
2. Load ALL `backtest_trades` for that run (`SELECT open_time, returns, commission ... ORDER BY open_time`).
3. HTTP call to `base-states`: `GET {BASE_STATES_URL}/api/history_by_asset?market={market}&symbol={symbol}` — returns daily regime classification for that symbol.
4. Build in-memory `regime_map: {date_str → regime_label}` from base-states response.
5. Group trades by `regime_map.get(trade_date, "UNCLASSIFIED")`.
6. For each regime bucket compute: trades count, pnl_usd, roi_pct, win_rate, profit_factor, max_drawdown.
7. Drop `UNCLASSIFIED` bucket.
8. Return JSON `{regime_name: {trades, pnl_usd, roi_pct, ...}, ...}`.

Nothing is persisted. The empty `dashboard_strategy_regimes` table is a defined-but-unused cache slot from migration 004.

## Implications for POMDP

**Bad news for the "ready Strategy × Regime matrix" hypothesis:** there is no such matrix in storage. To get per-regime performance for one strategy = 1 SQL query for trades + 1 HTTP call to base-states + in-memory aggregation. For 1670 strategies = 1670 backend round-trips, 1670 base-states calls.

**Good news on what does exist:**

- The **algorithm** for building Strategy × Regime is implemented and works (`get_run_regime_performance`).
- **`base-states /api/history_by_asset`** is the authoritative regime source — per-asset, daily granularity, queryable by symbol.
- **`backtest_trades`** is fully populated for strategies that have `backtest_runs` (all 1670 active should — that is what "Benchmark synced: 1670/1670" means).
- The regime taxonomy comes from `base-states`, not from JSON or another store. Need to confirm distinct regime labels by hitting `/api/history_by_asset` once.

## What this changes for POMDP-policy

POMDP cannot do a fast `SELECT ... FROM dashboard_strategy_regimes WHERE bucket = ?` to find best strategies for current regime. Two options:

**Option 1 — Build the cache.** Add a batch job that loops through all 1670 strategies, calls the existing `get_run_regime_performance` logic, and writes results into `dashboard_strategy_regimes`. The schema is already there. Most of the code is reusable from `backtests.py`. Estimated effort: 1-2 days. After that, POMDP-policy reads the cache directly.

**Option 2 — Read benchmark JSONB.** The `dev.strategies.benchmark` and `dev.strategies.data` JSONB columns may already contain per-regime stats from the benchmark backtest (the `regime_performance` field mentioned in block B — 24.9% coverage in original SQL). Worth re-checking exactly what is stored there now.

Note re screenshot: the "BY MARKET REGIME" table on screen IS the live-computed result from the endpoint above, not from any cache. Each time someone opens that strategys detail page, base-states gets hit + trades get aggregated. Acceptable for one user one strategy at a time, NOT acceptable for POMDP-policy ranking 1670 strategies per query.

**Recommendation:** Option 1. Build the cache. The schema exists, the algorithm exists, write a `bg_sync_regimes` task analogous to `bg_sync_metrics`.

## SQL queries that ARE worth running now

```sql
-- G1: confirm backtest_runs are populated (sanity check)
SELECT COUNT(*) AS run_count,
       COUNT(*) FILTER (WHERE is_benchmark) AS benchmark_runs
FROM dev.backtest_runs;

-- G2: how many runs have trades
SELECT COUNT(DISTINCT run_id) AS runs_with_trades,
       COUNT(*) AS total_trade_rows
FROM dev.backtest_trades;

-- G3: do strategies have benchmark backtests linked?
SELECT COUNT(*) AS strategies_with_benchmark
FROM dev.strategies
WHERE benchmark IS NOT NULL;
```

These confirm whether Option 1 (build cache) is straightforward — yes if all 1670 active strategies have benchmark runs with trades.

## What I am NOT 100% sure about, worth checking

- **Base-states regime taxonomy.** Need one call `GET /api/history_by_asset?market=whitebit&symbol=BTCUSDT` to see actual distinct regime labels and confirm there are ~10-12 (matching the screenshot). The label set lives in base-states, not in templates-ops.
- **`UNCLASSIFIED` bucket.** Endpoint drops it. For POMDP we may want to know how much of trade history is unclassified (signals stale regime detector or short history coverage in base-states).
- **Per-asset coverage in base-states.** History may exist only for major pairs (BTC, ETH, SOL). For altcoins regime detection may not exist, which means `UNCLASSIFIED = 100%` for those strategies.
