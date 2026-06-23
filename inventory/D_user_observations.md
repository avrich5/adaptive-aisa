# D — User Data Sources Inventory

**Repo root:** `~/wbprd_macbook/`
**Date:** 2026-06-05
**Method:** read-only code inspection

---

## 1. Chat Messages

### 1a. WB Chat — `ai-trading-strategy-advisor`

**Table:** `wb_chat_history` in `ai_orchestrator` PostgreSQL DB
**Model:** `backend/app/wb/db_models.py → WBChatHistory`

| Field | Type | Content |
|---|---|---|
| `id` | Integer PK | auto-increment |
| `request_id` | String(255) unique | UUID per request |
| `user_id` | String(255) nullable | WB user ID from `messages[0].context.user_id` — optional, may be null |
| `system_context` | JSONB | Full `messages[0].context`: `enabled_modes`, `balances`, `risk_preference`, `fee_rates`, `max_leverage`, `active_strategies` |
| `user_query` | Text | User's raw message text |
| `assistant_response` | Text | AI-generated answer |
| `strategies_returned` | JSONB | Strategy cards returned; null if no cards |
| `results_count` | Integer | Count of strategies in response |
| `detected_language` | String(10) | `en`, `ru`, `uk`, etc. |
| `is_fallback` | Boolean | Whether response used fallback path |
| `requested_asset` | String(50) | Asset extracted by query parser |
| `messages_count` | Integer | Total messages in turn (multi-turn length) |
| `processing_time_ms` | Integer | End-to-end latency |
| `peer_diagnostics` | JSONB | Cross-asset promotion audit |
| `created_at` | TIMESTAMP | Row creation time |

**Write path:** `POST /api/orchestrator/ask-wb` → background task `save_wb_chat_interaction` → `repository.save_wb_chat`.
**Read path:** `GET /api/orchestrator/wb-history` (paginated, optional `user_id` filter) → proxied through `profitradar-api` at `GET /api/v1/wb/history`.

**No sessionId field.** Each row is stateless — `request_id` is the only request identifier. `user_id` links rows to WB user but is optional and sent by WB frontend.

### 1b. Internal Advisor Sessions — `ai-trading-strategy-advisor`

**Tables:** `sessions` and `queries` in `ai_orchestrator` DB
**Models:** `backend/app/db/models.py`

**`sessions` table:**

| Field | Content |
|---|---|
| `id` | Integer PK |
| `session_id` | String(255) unique |
| `email` | User email |
| `catalog_name` / `catalog_display_name` | Active catalog |
| `started_at` / `ended_at` | Session boundaries |
| `total_queries`, `total_cost` | Aggregates |
| `ratings_good/neutral/bad`, `avg_rating` | Feedback aggregates |
| `openai_model` | Model used |
| `dataset_id` | Catalog dataset |

**`queries` table (per-message log):**

| Field | Content |
|---|---|
| `query_id` | String UUID |
| `timestamp` | Query time |
| `query_text` | User query text |
| `answer_text` | AI answer |
| `results_count` | Strategy results count |
| `semantic_used` | Boolean |
| `is_fallback` | Boolean |
| `requested_asset` | String |
| `rating` | -1 / 0 / 1 (user feedback) |
| `comment` | Text feedback |
| `top_strategies` | JSONB (strategies without backtesting_config) |
| `parsed_query` | JSONB (parser output) |

**Scope:** Internal advisor UI (`advisor.k3s.forvest.software`), not the WB-facing flow.

### 1c. In-memory Session History (orchestrator)

`backend/app/cache/session_cache.py → SessionCacheManager`
TTL 30 minutes. Stores last 8 messages (4 Q&A pairs) per `session_id` for conversation context. In-process only, not persisted to DB. Lost on restart.

---

## 2. WhiteBIT Integration — User Data

### 2a. What WB sends per request

On every `POST /api/v1/wb/chat` call, WB frontend sends `messages[0].context` (`WBChatSystemContext`):

| Field | Content | Stored? |
|---|---|---|
| `balances` | Dict: e.g. `{"collateral": 12000}` | Yes — `wb_chat_history.system_context` JSONB |
| `risk_preference` | `low` / `medium` / `risky` | Yes — same |
| `fee_rates` | Dict: `{"maker_pct": 0.01, "taker_pct": 0.055}` | Yes — same |
| `max_leverage` | Integer | Yes — same |
| `enabled_modes` | e.g. `["futures"]` | Yes — same |
| `user_id` | Optional WB internal user ID (string) | Yes — as `wb_chat_history.user_id` and inside `system_context` |
| `active_strategies` | Optional list of live positions with `entry_price, position_size_usdt, position_size_coins, unrealized_pnl_usdt, realized_pnl_usdt, realized_trades_count, total_commission_usdt` | Yes — stored in `system_context` JSONB |

**What is NOT pulled:** The platform does not call any WhiteBIT API directly to fetch user data. All data arrives as payload from WB frontend in each stateless request.

### 2b. WB Strategy Activation — `profitradar-api`

**Table:** `wb_strategies` in `skufs_profit_radar` DB
**Model:** `app/db/models/wb_strategy.py`

| Field | Content |
|---|---|
| `strategy_id` | PK — orchestrator strategy ID string |
| `allocated_capital` | Numeric — capital at activation |
| `leverage` | Integer |
| `max_drawdown_threshold` | Numeric |
| `sizing_factor` | Numeric |
| `status` | `active` / `deactivated` / `stopped` |
| `stop_reason` | String |
| `config` | JSONB — backtesting config from orchestrator |
| `sse_token_hash`, `sse_token_expires_at`, `sse_token_used_at` | SSE auth token lifecycle |
| `activated_at`, `stopped_at` | Timestamps |
| `activated_by`, `deactivated_by` | WB user ID (optional string, from request body) |

No `positions`, `trade_history`, or `balance` data in this table. Tracks strategy lifecycle only.

### 2c. WB Emulator Positions — `signal-emulator`

**Table:** `wb_emulator_positions` in `skufs_profit_radar` DB
**SQL:** `services/signal-emulator/src/db/queries/wb/wb_insert_position.sql`

Fields: `wb_strategy_id, symbol, side, mode, status, avg_entry_price, size, commission, tp_price, sl_price, current_step_index, max_steps`.

**No `user_id` field.** Linked to WB strategy via `wb_strategy_id` only.

### 2d. WB Emulator Signals — `signal-emulator`

**Table:** `wb_emulator_signals` in `skufs_profit_radar` DB
**SQL:** `services/signal-emulator/src/db/queries/wb/wb_insert_signal.sql`

Fields: `wb_strategy_id, signal_id, action, ticker, side, order_type, price, quantity, quantity_unit, stop_loss (JSONB), take_profit (JSONB), timestamp, position_id, indicator_payload (JSONB), meta (JSONB)`.

**No `user_id` field.** Strategy-scoped only.

### 2e. WB Audit Log — `profitradar-api`

**Table:** `wb_audit_log`
**Model:** `app/db/models/wb_audit_log.py`

Fields: `id, request_id, endpoint, method, response_status, latency_ms, created_at, client_ip, error_detail, strategy_id`.

Logs every `/api/v1/wb/*` request. No user payload content stored — only metadata (IP, endpoint, status, latency, strategy_id when resolvable).

---

## 3. UI Events — Clicks, Strategy Views, Time-on-Page

**отсутствует.** No third-party analytics SDK (PostHog, Mixpanel, Segment, Amplitude, gtag, GA4) is imported or called anywhere in `profitradar/src/`. Grep over the entire `src/` directory returned zero results for all common analytics call patterns (`track(`, `trackEvent`, `logEvent`, `posthog`, `mixpanel`, `dataLayer`).

`OperatorAnalytics.tsx` shows "Daily Active Users", "Cohort Retention", "Conversion Funnel" charts, but the data source is `generateAnalyticsData()` from `src/data/demo-data.ts` — hardcoded mock data. No real event collection behind it.

[UNKNOWN — requires clarification: server-side nginx access log on skufs may be the only source; need to check nginx config to confirm whether requests are logged per-user]

---

## 4. User Portfolio

### 4a. Portfolio Items — `profitradar-api`

**Table:** `portfolio_items` in `skufs_profit_radar` DB
**Model:** `app/db/models/portfolio.py`

| Field | Content |
|---|---|
| `id` | UUID PK |
| `user_id` | FK → `users.id` |
| `strategy_id` | FK → `strategies.id` |
| `status` | `active` / `paused` |
| `custom_name` | User-defined name for strategy (nullable) |
| `created_at`, `updated_at` | Timestamps |

Unique constraint: `(user_id, strategy_id)` — one entry per user per strategy.

### 4b. Portfolio Action Log

**Table:** `portfolio_action_log`
**Model:** `app/db/models/portfolio_action_log.py`

| Field | Content |
|---|---|
| `user_id` | FK → `users.id` |
| `strategy_id` | FK → `strategies.id` |
| `created_at` | Timestamp of action |
| `action` | `added` / `activated` / `paused` / `deleted` / `renamed` |
| `active_count`, `paused_count` | Portfolio state snapshot at action time |
| `old_name`, `new_name` | For `action=renamed` |

### 4c. How Portfolio is Updated

`UserTrackingMiddleware` on every authenticated JWT request: creates user if not exists (`get_or_create_user`), updates `users.last_active_at`, creates/updates `user_sessions` (device_info from User-Agent, ip_address).

Portfolio mutations via `POST/DELETE /api/v1/portfolio/*` endpoints. Each mutation appends a row to `portfolio_action_log`.

---

## 5. Request History Per User

### 5a. Platform-level — `profitradar-api`

**In-memory counter only.** `RequestLoggerMiddleware` (`app/core/middleware/request_counter.py`) increments `app.state.request_counts[endpoint]` per request path (not per user). Logged to stdout every 60s then reset. Not persisted to DB.

`user_sessions` table: tracks device, IP, `created_at`, `last_used_at`, `expires_at` per session. Not a request log — one row per device/session, not per API call.

**отсутствует** — no per-user request log stored to DB in `profitradar-api`. [UNKNOWN — requires clarification: nginx access log on skufs may capture all requests; not confirmed]

### 5b. WB Chat History — filterable by `user_id`

`wb_chat_history` in `ai_orchestrator` DB supports `GET /api/orchestrator/wb-history?user_id=X` — returns all chat turns for a given WB user ID. This is effectively a request history for the chat endpoint per WB user.

### 5c. Internal Advisor — per session/query log

`sessions` + `queries` tables in `ai_orchestrator` DB: full history of all queries for each internal advisor session, keyed by `session_id` and `email`.

---

## Summary Table

| Data Type | Table/Store | Key | Has userId? | Persisted? |
|---|---|---|---|---|
| WB chat turns | `wb_chat_history` (ai_orchestrator) | `request_id` | Yes (optional `user_id`) | PostgreSQL |
| WB system context (balances, risk, leverage) | `wb_chat_history.system_context` JSONB | same | Yes | PostgreSQL |
| WB active positions in context | `wb_chat_history.system_context.active_strategies` JSONB | same | Yes | PostgreSQL |
| WB strategy lifecycle | `wb_strategies` (skufs_profit_radar) | `strategy_id` | `activated_by`/`deactivated_by` (optional string) | PostgreSQL |
| WB emulator positions | `wb_emulator_positions` | `wb_strategy_id` | No (no user_id) | PostgreSQL |
| WB emulator signals | `wb_emulator_signals` | `wb_strategy_id` | No (no user_id) | PostgreSQL |
| WB API audit | `wb_audit_log` | `request_id` | No (client_ip only) | PostgreSQL |
| Internal advisor sessions | `sessions` (ai_orchestrator) | `session_id`, `email` | `email` | PostgreSQL |
| Internal advisor queries | `queries` (ai_orchestrator) | `query_id` | via `session_id` | PostgreSQL |
| Platform user portfolio | `portfolio_items` | `user_id` | Yes | PostgreSQL |
| Portfolio action audit | `portfolio_action_log` | `user_id` | Yes | PostgreSQL |
| Emulator signals (PR users) | `emulator_signals` | `user_id` | Yes | PostgreSQL |
| Emulator positions (PR users) | `emulator_positions` | `user_id` | Yes | PostgreSQL |
| User profile | `users` | `id` (Supabase UUID) | Yes | PostgreSQL |
| User sessions | `user_sessions` | `user_id` | Yes | PostgreSQL |
| UI clicks / page views | — | — | No | **отсутствует** — no event collection in frontend code |
| Request log per user | — | — | No | **отсутствует** — in-memory counter only, resets every 60s |
| In-memory chat history (advisor) | `SessionCacheManager` | `session_id` | Yes | In-process only, TTL 30 min |
