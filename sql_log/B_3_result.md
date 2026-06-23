# B3 Result — Per-Regime Metrics Coverage

Query executed: 2026-06-05
DB: 77.42.77.82:5432/ai_orchestrator, schema: dev

Original query checked wrong paths. Extended query confirmed actual location of per-regime data.

```sql
-- Original query (paths from spec):
SELECT COUNT(*) as has_per_regime
FROM dev.strategies
WHERE data -> 'quality_metrics' -> 'per_regime' IS NOT NULL
   OR data -> 'aggregate_stats' -> 'per_regime' IS NOT NULL
   OR data -> 'market_context' -> 'regime_performance' IS NOT NULL;
```
Result: **0**

```sql
-- Correct path (top-level field in unified JSON v7.3):
SELECT COUNT(*) as has_regime_performance_toplevel
FROM dev.strategies
WHERE data -> 'regime_performance' IS NOT NULL
  AND data ->> 'regime_performance' != 'null';
```
Result: **4161**

```sql
-- benchmark_periods (per-interval regime rows, main source for regime_fit):
SELECT COUNT(*) as has_benchmark_periods
FROM dev.strategies
WHERE data -> 'market_context' -> 'benchmark_periods' IS NOT NULL
  AND jsonb_array_length(data -> 'market_context' -> 'benchmark_periods') > 0;
```
Result: **16488**

Summary:
- Per-regime metrics at paths specified in task (quality_metrics/aggregate_stats/market_context subkeys): **0** — those paths do not exist in actual schema.
- Top-level `data.regime_performance` (v7.3 field): **4161 / 16709 = 24.9%**
- `data.market_context.benchmark_periods` (per-interval regime rows used by orchestrator for regime_fit): **16488 / 16709 = 98.7%**
