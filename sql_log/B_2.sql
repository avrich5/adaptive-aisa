-- B2: Coverage of key fields
-- NOTE: Column names corrected after B4 schema check.
-- Original spec used benchmark_data/wb_capital_data — actual names are benchmark/wb_context.
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN data IS NOT NULL AND data::text != 'null' THEN 1 END) as has_data,
  COUNT(CASE WHEN benchmark IS NOT NULL AND benchmark::text != 'null' THEN 1 END) as has_benchmark,
  COUNT(CASE WHEN wb_context IS NOT NULL AND wb_context::text != 'null' THEN 1 END) as has_wb_context
FROM dev.strategies;
