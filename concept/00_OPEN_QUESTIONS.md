# Open Questions — POMDP Inventory

**Дата:** 2026-06-05
Всі [UNKNOWN] позначки з документів інвентаризації.

---

## З блоку A (оркестратор)

| # | Питання | Що треба для відповіді |
|---|---------|----------------------|
| A1 | Яка точна таблиця/запит у `get_settings_params(brute_id, settings_id)`? | Читати `app/rag_retriever.py` в `ai-trading-strategy-advisor` |
| A2 | Який тип pgvector індексу — IVFFlat чи HNSW? | Читати `migrations/000_install_pg_vector.sql` |
| A3 | Які саме поля unified JSON конкатенуються для генерації embedding? | Читати `scripts/generate_embeddings.py` |

---

## З блоку B (стратегії)

| # | Питання | Що треба для відповіді |
|---|---------|----------------------|
| B1 | Точна формула `priority_tier` в генераторі — це `profitable_pct == 100`? | Читати `unified_generator.py` рядки навколо `priority_tier` assignment |
| B2 | Яка частка рядків у `wb_chat_history` має `user_id IS NULL`? | SQL: `SELECT COUNT(CASE WHEN user_id IS NULL THEN 1 END)::float / COUNT(*) FROM wb_chat_history` на `ai_orchestrator` |
| B3 | Яку схему читає `text_builder.py` (точні field names)? | Читати `text_builder.py` в `llm-training-data-miner` — підтвердити mismatch |
| B4 | Чи є `regime_performance` в dataset_id=14 або тільки в 15/16/17/18? | SQL: `SELECT dataset_id, COUNT(*) FROM dev.strategies WHERE data->>'regime_performance' IS NOT NULL GROUP BY dataset_id` |

---

## З блоку C (режими)

| # | Питання | Що треба для відповіді |
|---|---------|----------------------|
| C1 | Точний дата-діапазон `all_regimes.parquet` (Binance і WhiteBIT)? | На skufs: `python3 -c "import pandas as pd; df=pd.read_parquet('~/base_states_skufs/data/pipeline_output/binance/all_regimes.parquet'); print(df.index.min(), df.index.max())"` |
| C2 | Яке значення `UPDATE_INTERVAL_MINUTES` у `.env` на skufs? | `cat ~/base_states_skufs/.env \| grep UPDATE_INTERVAL` |
| C3 | Скільки днів реально мають R9 і R10 у Binance parquet (Markov рядки тонкі)? | На skufs: `python3 -c "import pandas as pd; df=pd.read_parquet(...); print(df[df.regime.isin(['R9_SPECULATIVE_MANIA','R10_LIQUIDITY_STRESS'])].groupby('regime').size())"` |
| C4 | `danger_score` і `priority_score` — доступні через `/api/risk` на skufs? | `curl http://192.168.1.11:8002/api/risk` або перевірити роути в `app/server.py` |

---

## З блоку D (користувач)

| # | Питання | Що треба для відповіді |
|---|---------|----------------------|
| D1 | Nginx access log на skufs логує per-request з user_id або тільки IP? | `cat /etc/nginx/nginx.conf` або `sudo nginx -T` на skufs |
| D2 | Яка частка `wb_chat_history.user_id IS NULL`? | SQL: `SELECT COUNT(CASE WHEN user_id IS NULL THEN 1 END), COUNT(*) FROM wb_chat_history` на `ai_orchestrator` |

---

## З блоку E (gap analysis)

| # | Питання | Що треба для відповіді |
|---|---------|----------------------|
| E1 | Підтверджена формула `priority_tier` — `profitable_pct == 100`? | Andriy або Denis, знають умисел |
| E2 | Чи є плани покрити `regime_performance` для решти 75.1% стратегій? | Denis / Женя — статус pipeline run для старих датасетів |
| E3 | `benchmark_periods` баг — чи вже виправлений в generator v7.3? | Читати CHANGELOG або останній commit у `unified_generator.py` |

---

## Пріоритет розв'язання

**Blocker для POMDP-старту:**
- C1 (дата-діапазон parquet — базовий факт для transition matrix якості)
- B4 (в яких датасетах є `regime_performance` — визначає обсяг роботи)
- E3 (чи вже виправлений `benchmark_periods` — від цього залежить чи можна використовувати поточний regime-fit)

**Потребує SQL-запиту (5 хвилин):**
- B2, D2 (частка null user_id — критично для User State feasibility)
- B4 (розподіл regime_performance по датасетах)
