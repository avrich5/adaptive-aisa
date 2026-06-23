# B2 Result — Coverage of Key Fields

Query executed: 2026-06-05
DB: 77.42.77.82:5432/ai_orchestrator, schema: dev

NOTE: Actual column names are `benchmark` and `wb_context` (not `benchmark_data`/`wb_capital_data` as in original spec).
B4 query confirmed the actual schema before running this.

```sql
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN data IS NOT NULL AND data::text != 'null' THEN 1 END) as has_data,
  COUNT(CASE WHEN benchmark IS NOT NULL AND benchmark::text != 'null' THEN 1 END) as has_benchmark,
  COUNT(CASE WHEN wb_context IS NOT NULL AND wb_context::text != 'null' THEN 1 END) as has_wb_context
FROM dev.strategies;
```

| total | has_data | has_benchmark | has_wb_context |
|-------|----------|---------------|----------------|
| 16709 | 16709    | 10418         | 8548           |

Coverage rates:
- `data` (unified JSON): 100% (16709/16709)
- `benchmark`: 62.3% (10418/16709)
- `wb_context`: 51.2% (8548/16709)
