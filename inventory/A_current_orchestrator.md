# A — Current Orchestrator Inventory

**Repo:** `ai-trading-strategy-advisor`
**Path:** `backend/app/`
**Date:** 2026-06-05
**Branch:** development @ a6a3709

---

## 1. Entry Points — FastAPI Endpoints

Two endpoints accept user messages:

**`POST /api/orchestrator/ask`** (`app/main.py`, line 434)
- Request model: `QueryRequest`
- Fields parsed from request: `request.query` (user message), `request.session_id`, `request.market` (optional regime venue), `request.internal_preview` (optional QA flag)
- Session lookup: `get_or_load_session(request.session_id, db)` — loads `SessionCache` from in-memory cache or DB
- Calls: `orchestrator.process_query(request.query, conversation_history, openai_model, market)`
- History source: `session_cache.recent_history` (in-process list, max 8 messages / 4 Q&A pairs)

**`POST /api/orchestrator/ask-wb`** (`app/wb/router.py`, line 83)
- Request model: `WBChatRequest` — contains `messages: List[WBMessage]` (full history on every call, stateless protocol)
- Extracts: `query_text, prior_history = history.split_messages_for_orchestrator(body.messages)`, `system_ctx = body.messages[0].context` (type `WBSystemContext`)
- Calls: `orchestrator.process_query(enriched_query, prior_history, openai_model, market, user_profile, endpoint_label="ask-wb")`
- `WB_REGIME_MARKET` hardcoded to `"whitebit_futures"` for this endpoint

No other endpoint invokes `orchestrator.process_query`. The `/api/v1/regime/snapshot` endpoint is read-only. The `/api/orchestrator/wb-backtesting-config` endpoint reads KB data but does not run the RAG pipeline.

---

## 2. Observation Extraction — Fields Parsed from User Input

**`/api/orchestrator/ask` — `QueryRequest` model:**
- `query` (str) — user message text
- `session_id` (str) — used to look up conversation history and model selection
- `market` (Optional[str]) — regime venue filter (`whitebit_futures` | `binance_futures`)
- `internal_preview` (Optional[InternalPreviewSpec]) — QA bypass flag; no user text content
- No `userId` field at this level. No explicit `history` in the request body — history comes from server-side session cache.

**`/api/orchestrator/ask-wb` — `WBChatRequest`** (`app/wb/models.py`):
- `messages: List[WBMessage]` — full conversation history on every call
- `messages[0].context: WBSystemContext` — system context containing:
  - `user_id` (Optional[str]) — WhiteBIT user identifier, stored in `wb_chat_history.user_id`
  - `balances: Dict[str, float]`
  - `risk_preference: Literal["low", "medium", "risky"]`
  - `fee_rates: Dict[str, float]`
  - `max_leverage: int`
  - `active_strategies: Optional[List[WBActiveStrategy]]`
- `internal_preview` (Optional[InternalPreviewSpec])

**`QueryParser.parse()` — fields extracted from query text** (`app/orchestrator/query_parser.py`):
- `assets` — list of recognized crypto ticker symbols (matched against KB index)
- `indicators` — list of recognized indicator names (matched against KB index with word-boundary regex)
- `excluded_indicators` — indicators negated by phrases like "without RSI", "no MACD"
- `min_roi` — integer % threshold (regex: ~10 patterns)
- `max_mdd` — float % threshold (regex: ~18 patterns)
- `min_fitness` — float threshold (regex: 5 patterns)
- `min_trades_per_interval` — float (regex: 6 patterns)
- `max_trades_per_interval` — float (1 pattern)
- `max_stop_loss` — float % (5 patterns)
- `min_take_profit` — float % (5 patterns)
- `limit` — int (4 patterns, for "top N" queries)
- `intent` — one of: `educational`, `reliable`, `best_reliable`, `find_best`, `explain`, `compare`, `general`
- `asset_class` — `crypto` | `stocks` | `forex` (keyword detection)
- `keywords` — all words > 3 chars from query (for keyword scoring)

Text is processed in English. Non-English input is translated before parsing via `TranslationService.translate_to_english()`.

---

## 3. Context Pulled Per Request

**At startup (loaded once into memory):**
- PostgreSQL `dev.strategies` table — full strategy corpus loaded into `KnowledgeBase.strategies` dict (keyed by `brute_id`)
  - Columns read: `brute_id`, `data` (JSONB unified JSON), `benchmark` (JSONB), `wb_context` (JSONB), `embedding` (vector, if in-memory mode)
  - Filtered by `dataset_id`
- `strategy_kpi` table — all R² values loaded into in-process `R2Cache` via `kpi_repo.get_all_min_r2()`
- 5 metadata JSON files from `backend/data/`: `orchestrator_metadata.json`, `available_indicators.json`, `available_assets.json`, `available_patterns.json`, `coverage_report.json`

**Per request:**
- Session conversation history: from in-process `SessionCacheManager` (TTL 30 min); on cache miss, loaded from PostgreSQL `sessions` + `queries` tables (last 4 queries = 8 messages)
- For `ask-wb`: no session lookup — full history in request body; `WBUserProfile` built from `body.messages[0].context`
- Regime snapshot: loaded from in-process `RegimeService` (refreshed daily from DB, no per-request DB query)
- R² values for top-3 strategies: read from in-process `R2Cache` (loaded at startup)
- Settings params (only when query contains "parameter/setting/indicator/exact/specific"): async DB read via `SimpleRetriever.get_settings_params(brute_id, settings_id)` — [UNKNOWN — requires clarification: exact table/query in `app/rag_retriever.py`]

**Columns from `dev.strategies` actually used:**

| Column | Used for |
|---|---|
| `brute_id` | Primary key for all KB indexes |
| `data` (JSONB) | Full unified JSON: `strategy_concept.name`, `trading_logic_description.indicators_used`, `factual_description.actionable_guidance`, `factual_description.performance_overview`, `factual_description.risk_assessment`, `factual_description.signal_quality`, `quality_metrics.priority_tier`, `aggregate_stats.avg_roi`, `aggregate_stats.avg_fitness`, `aggregate_stats.avg_win_rate`, `market_context.asset` |
| `benchmark` (JSONB) | `roi_avg`, `mdd_avg`, `signal_frequency`, `profit_factor`, `win_rate` — overlay onto unified JSON KPIs |
| `wb_context` (JSONB) | `performance.mdd_avg` — used in WB backtesting config; also passed into WB filter logic |
| `embedding` (vector) | In-memory cosine similarity search (1536-dim, loaded as `np.ndarray`) |
| `dataset_id` | Filter at load time |

---

## 4. Semantic Search

**Embedding model:** `text-embedding-3-small` (OpenAI) — confirmed in `app/semantic_search.py` line 66 and `scripts/generate_embeddings.py`

**Index type:** Two modes controlled by `settings.SEMANTIC_SEARCH_IN_MEMORY`:
- **In-memory (NumPy):** All strategy embeddings loaded as `np.ndarray` into `KnowledgeBase.embeddings` dict at startup; cosine similarity computed via `np.dot / (norm * norm)` — brute-force O(N)
- **Database (pgvector):** `embedding <=> CAST(:query_emb AS vector)` cosine distance operator; index type — [UNKNOWN — requires clarification: IVFFlat vs HNSW not verified from reviewed files, check migration `000_install_pg_vector.sql`]

**Fields indexed:** The `embedding` column in `dev.strategies` stores a 1536-dimensional vector generated from the unified JSON text. Exact field(s) used for embedding generation — [UNKNOWN — requires clarification: check `scripts/generate_embeddings.py` for the text concatenation logic]

**Top-k value:** `top_k=50` — confirmed in `app/orchestrator/rag_searcher.py` line 214

**Hybrid scoring:** `final_score = 0.4 × keyword_score + 0.6 × semantic_score`

---

## 5. Fact Extraction

**Method:** Structured field access — no regex on arbitrary text at extraction stage. `FactExtractor.extract()` (`app/orchestrator/fact_extractor.py`) reads pre-structured sub-fields from the unified JSON `data` dict:

- `data['factual_description']['performance_overview']` — list of strings, takes first 2 per strategy
- `data['factual_description']['actionable_guidance']` — list of strings, takes first 2 per strategy
- `data['factual_description']['risk_assessment']` — list of strings, takes first 1 per strategy

Prefixes each fact with `[brute_id]`. Returns up to 20 total facts from top 10 results.

**Numeric metric extraction — uses regex on string fields** (`app/orchestrator/benchmark_kpis.py`):

`parse_guidance_kpis()` applies regex to `actionable_guidance` strings:
- ROI: `r"([\d.]+)%\s*ROI"` on lines containing `"Performance:"`
- fitness: `r"([\d.]+)\s*fitness"`
- profit factor: `r"([\d.]+)\s*profit factor"`
- max drawdown: `r"([\d.]+)\s*max drawdown"`
- trades/day: `r"Signal frequency:\s*([\d.]+)\s*trades/day"` on `signal_quality` strings
- settings_id: `r'settings_id\s+(\d+)'` on `actionable_guidance` strings

**Benchmark overlay** (`overlay_benchmark_kpis()`): when `benchmark` JSONB is present, structured numeric fields (`roi_avg`, `mdd_avg`, `signal_frequency`, `profit_factor`) directly override regex-extracted values.

---

## 6. Final Synthesis

**LLM:** OpenAI, model configurable. Default: `gpt-4o-mini` (env `OPENAI_MODEL`). Per-session model override supported via `session_cache.openai_model`. For `ask-wb`, `get_default_model()` is used (loaded at startup from OpenAI API).

**API call parameters:** `temperature=0.3`, `max_tokens=200` (or `max_completion_tokens=200` for `gpt-5` prefix models)

**Context window sent to GPT** (built in `GPTSynthesizer._build_context()` + `synthesize()`):

System prompt contains:
- Role definition ("AI Trading Advisor for ProfitRadar.io")
- 8 critical rules: no strategy listing, 2-3 sentence summary, highlight top pick, confidence level, market regime integration instructions
- Terminology mapping (tier names)
- Response format: under 100 words
- Conditional additions: personalization block (WB user collateral + risk), language instruction (if non-English)

User message contains:
- `query` (English pipeline text)
- Optional `market_context_str` — regime block from `build_market_context_block()` and/or `build_regime_filter_block()` (injected when regime-related or regime filter active)
- `context` block with:
  - `Total strategies analyzed: N`
  - Top 5 strategy names with asset, tier, ROI, MDD
  - Up to 15 fact lines from `FactExtractor` (brute_id references hidden via `translator.hide_brute_id()`)

**Conversation history:** Last 4 messages (2 Q&A pairs) from `conversation_history[-4:]` prepended before the user message. For `ask-wb`, history comes from request `body.messages`; orchestrator receives the slice prior to the last user message.

---

## 7. User State

**`/api/orchestrator/ask` (session-based flow):**

User state exists and is server-side. Storage: in-process `SessionCacheManager` (Python dict, TTL 30 min, no Redis). Persistent backing: PostgreSQL `sessions` and `queries` tables.

Session contains:
- `session_id` (str) — generated at `POST /api/sessions/start` from email + catalog_name + timestamp
- `email` — user identifier
- `openai_model` — model selected at session start
- `dataset_id` — dataset selected at session start
- `recent_history: List[Dict]` — last 8 messages (4 Q&A pairs), format `[{role, content}, ...]`
- Stats counters: `total_queries`, `total_cost`, `ratings_good/neutral/bad`, `avg_rating`

Conversation memory: `recent_history` is passed to `orchestrator.process_query()` as `conversation_history`. GPT synthesis uses last 4 of these messages (`conversation_history[-4:]`). Context inheritance (assets/indicators from prior query) is handled by `_detect_context_reference()` in the orchestrator — inspects up to 6 prior user messages for `min_roi` inheritance.

**`/api/orchestrator/ask-wb` (stateless WB flow):**

No server-side session state. Full conversation history is sent on every request in `body.messages`. No session_id. The `user_id` field in `WBSystemContext` is stored to `wb_chat_history` for logging only — it is not used to look up state. Conversation memory for GPT: `prior_history` extracted from `body.messages` (all prior assistant+user turns before the last user message).

**Conclusion:** For the `ask` endpoint, server-side session state with in-process conversation memory exists. For the `ask-wb` endpoint, user state is **отсутствует** — all state carried by the client in the request body.
