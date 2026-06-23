# F — profitradar-templates-ops inventory

Added 2026-06-05 after Andriy flagged this repo was missed in the original inventory pass.
Repo path: `/Users/andriy/wbprd_macbook/profitradar-templates-ops`

## What it is

Internal Strategy Dashboard. React + TypeScript frontend, FastAPI single-file backend (`backend/main.py`). Three tabs: Catalog, Detail, Live. This is the source of the screenshots Andriy shared (1670 strategies, per-regime tables).

Powers `app.profitradar.io` dashboard. Not user-facing — internal tool for analysing the strategy library.

## Data sources

Backend connects to **two PostgreSQL databases**:

- `profit_radar` — multi-schema (`dev` / `stage`), gated by `X-DB-Schema` HTTP header. Holds templates, backtests, metrics cache, portfolio proxy tables.
- `ai_orchestrator` — always reads literal `dev.` prefix. Factory datasets and strategies. Header is ignored on these routes.

Also reads filesystem CSVs via the `scalping-pnl` service for equity curves on cache miss.

## Metrics cache — this is the key finding

Migration 004 (`backend/migrations/004_create_metrics_cache.sql`) creates four cache tables in **both** `dev` and `stage` schemas of `profit_radar`:

1. **`dashboard_strategy_metrics`** — flat aggregate per strategy: ROI, Sharpe, MDD, win rate, etc. Primary key `id = "{brute_id}-{settings_id}"`. Drives Catalog page.

2. **`dashboard_strategy_windows`** — same metrics computed over ALL / 6M / 3M / 1M windows. Primary key `(template_id, window)`. Populated lazily on first Detail page visit.

3. **`dashboard_strategy_equity`** — equity curve as JSONB arrays (`dates`, `values`).

4. **`dashboard_strategy_regimes`** — **this is the Strategy × Regime matrix we need for POMDP-policy.** Schema:
   ```
   template_id   TEXT
   bucket        TEXT          -- regime name (matches base-states regime taxonomy)
   trades        INTEGER
   pnl_usd       DOUBLE PRECISION
   roi_pct       DOUBLE PRECISION
   win_rate      DOUBLE PRECISION
   profit_factor DOUBLE PRECISION
   max_drawdown  DOUBLE PRECISION
   synced_at     TIMESTAMPTZ
   PRIMARY KEY (template_id, bucket)
   ```

   Source of truth: computed from `backtest_trades` joined with regime tags. Cache rebuilt by `bg_sync_metrics` background task on startup; advisory lock prevents duplicate work across replicas.

   **One row per (strategy, regime) pair.** For 1670 strategies × 12 regimes = up to 20040 rows. This is the matrix POMDP-policy needs to read.

## Per-regime breakdown on Detail page

Detail view does NOT read `dashboard_strategy_regimes` directly for the live per-regime table shown in screenshot 1. Instead it calls `profitradar-api`:

```
GET /proxy/strategies/{id}/kpi
```

(via `useStrategyKpi` in `frontend/src/pages/strategy-dashboard/api/strategies.ts`)

This means there are **two parallel sources** of per-regime data:
- `profit_radar.dev.dashboard_strategy_regimes` — cached, computed by templates-ops backend
- `profitradar-api` KPI endpoint — what UI actually reads

Need to verify whether these agree, and which one POMDP should read. Most likely `dashboard_strategy_regimes` is the better choice for batch reads (whole library at once), and KPI endpoint is for single-strategy detail view.

## Live regime (current market state)

Frontend reads current market regime from a separate service called `base-states`:

```
GET /proxy/base-states/summary?market=whitebit  (5 min poll)
GET /proxy/base-states/live?market=whitebit     (5 min poll)
```

(via `useCurrentRegime` and `useLiveState` in `regimes.ts`)

This is the realtime regime detector that POMDP-policy will need to query for "what market state are we in right now". Base-states is already in repos sync log, was pulled at 4ff792d.

## What this changes vs original B/C blocks

**B (strategies coverage):** Original block did SQL on `dev.strategies` only. Did not find `dev.dashboard_strategy_regimes` or `stage.dashboard_strategy_regimes`. Need a follow-up SQL:

```sql
-- How many strategies have per-regime cache rows
SELECT COUNT(DISTINCT template_id) AS strategies_with_regime_cache,
       COUNT(*) AS total_regime_rows,
       COUNT(DISTINCT bucket) AS distinct_regimes
FROM dev.dashboard_strategy_regimes;

-- Per-strategy regime coverage
SELECT template_id, COUNT(*) AS regime_count
FROM dev.dashboard_strategy_regimes
GROUP BY template_id
ORDER BY regime_count;
```

If `COUNT(DISTINCT template_id)` ≈ 1670 and `regime_count` ≈ 10-12 per strategy → **B4 fully closed, Strategy × Regime matrix is ready for POMDP-policy as a SQL JOIN**.

**C (market regimes):** Original block looked for `all_regimes.parquet`. The dashboard reads regime info from two different places: cached per-strategy aggregates (`dashboard_strategy_regimes.bucket`) and live regime detector (`base-states`). The mapping between these two regime taxonomies needs to be confirmed — they may use different labels.

**A (orchestrator):** Templates-ops is a separate consumer of `dev.strategies.data` JSONB (exposed via "Show Unified JSON" button). Confirms unified JSON IS used outside the orchestrator. Original block A noted only orchestrator as consumer. Add templates-ops as second consumer.

## Endpoints POMDP-policy can use directly

If POMDP is built on top of existing infrastructure rather than from scratch:

| Need | Endpoint / Table |
|------|-----------------|
| Current market regime | `base-states /api/summary?market=whitebit` |
| All strategies + base metrics | `dev.dashboard_strategy_metrics` (PG direct, fast) |
| Per-strategy per-regime performance | `dev.dashboard_strategy_regimes` (PG direct, batch-friendly) |
| Per-strategy live KPI | `profitradar-api GET /api/v1/strategies/{id}/kpi` |
| Equity curve | `dev.dashboard_strategy_equity` (PG direct) |

All four exist today. POMDP-policy does not need to compute per-regime aggregates from scratch.

## Open follow-ups for this block

- F1: Run the SQL above to confirm `dashboard_strategy_regimes` coverage for the 1670 active strategies. ETA 30 sec.
- F2: Compare regime taxonomy: `dashboard_strategy_regimes.bucket` distinct values vs `base-states` summary endpoint output. Need to know if they align.
- F3: Read `profitradar-api` source for `GET /strategies/{id}/kpi` to understand if it agrees with `dashboard_strategy_regimes` or computes differently.
