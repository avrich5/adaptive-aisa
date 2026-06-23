# B4 Result — Column List of dev.strategies

Query executed: 2026-06-05
DB: 77.42.77.82:5432/ai_orchestrator, schema: dev

```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'dev' AND table_name = 'strategies'
ORDER BY ordinal_position;
```

| column_name | data_type                   |
|-------------|-----------------------------|
| id          | integer                     |
| dataset_id  | integer                     |
| brute_id    | character varying           |
| data        | jsonb                       |
| embedding   | USER-DEFINED (pgvector)     |
| created_at  | timestamp without time zone |
| benchmark   | jsonb                       |
| wb_context  | jsonb                       |

Total: 8 columns.

Note: No `benchmark_data` or `wb_capital_data` columns exist. The actual column names are
`benchmark` and `wb_context`. This was confirmed before running B2.
