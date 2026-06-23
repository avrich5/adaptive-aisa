-- B3: Check for per-regime metrics in data column
SELECT
  COUNT(*) as has_per_regime
FROM dev.strategies
WHERE data -> 'quality_metrics' -> 'per_regime' IS NOT NULL
   OR data -> 'aggregate_stats' -> 'per_regime' IS NOT NULL
   OR data -> 'market_context' -> 'regime_performance' IS NOT NULL;
