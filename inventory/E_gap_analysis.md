# Gap Analysis: що є vs що потрібно для POMDP-архітектури

**Дата:** 2026-06-05
**Джерела:** блоки A (оркестратор), B (стратегії), C (режими), D (користувач),
investigation_factual_description.md, 04_unified_json_v7_3_review.md, 07_factual_description_critical_review.md

---

## 1. User State estimation

**Що є:**

- `wb_chat_history` (PostgreSQL `ai_orchestrator`): `user_id` (optional string), `user_query`, `assistant_response`, `system_context` JSONB (balances, risk_preference, fee_rates, max_leverage, enabled_modes, active_strategies), `created_at`. Один рядок на запит. Без sessionId — рядки пов'язані через `user_id` опційно.
- `WBSystemContext` на кожному запиті: `risk_preference` (low/medium/risky), `max_leverage` (int), `balances.collateral` (float), `fee_rates`, `active_strategies` (entry_price, position_size_usdt, unrealized_pnl_usdt, realized_pnl_usdt, realized_trades_count, total_commission_usdt).
- Internal advisor: `sessions` + `queries` tables (`email`, `session_id`, per-query `rating` -1/0/1, `comment`, `parsed_query` JSONB, `top_strategies` JSONB).
- `portfolio_items` + `portfolio_action_log`: `user_id`, `strategy_id`, `action` (added/activated/paused/deleted/renamed), `active_count`, `paused_count`, `created_at`.
- `QueryParser.parse()` витягує з тексту запиту: `assets`, `indicators`, `intent`, `min_roi`, `max_mdd`, `max_stop_loss`, `min_trades_per_interval`, `limit`, `keywords`.
- Conversation memory: останні 4 повідомлення в GPT-контексті (8 у session cache, TTL 30 хв). Для WB — весь prior_history в тілі запиту.

**Що потрібно (POMDP):**

- Дискретний простір S_user: прихований стан користувача (explorer, position_manager, yield_seeker, professional тощо) — клас поведінки, а не атрибут профілю.
- Спостереження o_t: фіча-вектор з кожного звернення → вхід для belief update.
- Observation model P(o|s): ймовірність набору спостережень за умови прихованого стану.
- Transition model P(s'|s, a): як стан змінюється після дії системи.
- Belief state b_t = P(s_t | o_1..t, a_1..t-1): posterior по всіх зверненнях.

**Gap:**

1. Немає прихованого стану користувача — ні в БД, ні в коді. `intent` enum (7 значень) — це класифікація одного запиту, не стан користувача.
2. `user_id` опційний у WB-потоці: 47–50% взаємодій можуть не мати user linkage. [UNKNOWN — потрібна аналітика по `wb_chat_history.user_id IS NULL`]
3. Немає accumulation спостережень по часу. `wb_chat_history` зберігає рядки, але ніде не агрегується в belief vector. Кожен запит незалежний.
4. Немає моделі переходів між станами: відсутній будь-який код, що оцінював би P(s'|s, a).
5. UI-події (кліки, перегляди карток, час на сторінці) відсутні цілком — нема аналітики в фронтенді (підтверджено grep-ом).
6. `portfolio_action_log` є, але не консьюмується оркестратором при формуванні відповіді.
7. `ratings_good/neutral/bad` є в advisor sessions, але не піднімаються до рівня belief update.
8. Немає history lookup за `user_id` на рівні оркестратора для WB-flow — лише raw лог в `wb_chat_history`.

---

## 2. Market State estimation

**Що є:**

- 12 режимів (R1–R12) + MIXED + UNCLASSIFIED: детерміністичний rule-based каскад (`classify_regime()` в `pipeline/state_rules.py`). Пріоритетна черга — fixed order перевірок.
- Per-asset класифікація: BTC (вага 0.35), ETH (0.20), BNB/SOL/XRP (0.10), ADA (0.08), DOGE (0.07). Composite state з weighted consensus.
- Daily timeframe (OHLCV 1d). 252-денний warmup. Features: ~20 percentile-нормалізованих індикаторів (EMA slope, ADX, ATR, BB width, realized vol, volume z-score, return percentiles, drawdown).
- Transition matrix в пам'яті: Markov (70%) + proximity (30%) blending → `GET /api/transition`. Будується з `all_regimes.parquet` при старті.
- Live detection: `get_live_snapshot()` — класифікація з open (незакритою) свічкою, прапор `preliminary_warning: true`. Фінальний результат лише після daily close (00:05 UTC).
- `all_regimes.parquet` — per-asset per-day мітки. Дата-діапазон: [UNKNOWN — файл не на MacBook].
- R12 (REGIME_TRANSITION) вставляється як post-processing маркер на межах груп — не є output правил.
- R9, R10 мають `DATA_SUFFICIENCY = "proxy"` (рідкісні події, тонка вибірка для Markov рядків).

**Що потрібно (POMDP):**

- Дискретний простір режимів.
- Real-time або near-real-time детекція (або явне визначення затримки).
- Transition matrix.

**Gap:**

1. Дискретний простір є (R1–R12 + MIXED), але R12 — post-processing маркер, не справжній стан. Включати R12 в POMDP transition matrix семантично некоректно.
2. `all_regimes.parquet` недоступний на MacBook (git-ignored). Дата-діапазон і якість Markov рядків для R9/R10 невідомі без файлу.
3. Daily granularity: between-day intra-day зміни режиму не відстежуються. Для POMDP це означає максимум 1 belief update на добу по ринковому стану.
4. `benchmark_periods` в unified JSON — системний баг (підтверджено в 04_unified_json_v7_3_review.md): один часовий інтервал дублюється для R1, R2, R3 з різними мітками. `compute_strategy_regime_fit` в оркестраторі працює на цих даних → regime-fit cascade видає неправильні результати для стратегій де benchmark_periods сформований так.
5. Mapping year-based → regime labels в старих `benchmark_periods` (2022→bear, 2023→bull): точність залежить від вирівнювання інтервалів з реальними режимними межами. Не верифіковано.
6. `danger_score` і `priority_score` не обчислюються в orchestrator і не публікуються через API base-states у вигляді, доступному поточному оркестратору. [UNKNOWN — потрібно перевірити `/api/risk` endpoint на skufs].

---

## 3. Strategy profiles

**Що є:**

- 16709 стратегій у 16 датасетах (`ai_orchestrator.dev.strategies`).
- `data` (unified JSON, 100%): містить `strategy_concept`, `trading_logic_description`, `factual_description`, `quality_metrics`, `aggregate_stats`, `market_context`.
- `benchmark` (62.3% = 10418): overlay ROI/MDD/signal_frequency/profit_factor — реально використовується оркестратором.
- `wb_context` (51.2% = 8548): `regime_risk_flags.negative_in[]` — hard drop стратегії якщо поточний режим у списку.
- `regime_performance` (top-level v7.3, 24.9% = 4161): per-regime dict {R1: {roi, trades, fitness, winrate}, R2: ...}. Оркестратор не читає цей блок.
- `market_context.benchmark_periods` (98.7% = 16488): використовується `compute_strategy_regime_fit`. Баг: дублікати з різними мітками (підтверджено на dataset_id=14/15).
- `quality_metrics.oos_roi`, `oos_mdd` (v7.3): є в JSON як числові поля, оркестратор не читає — продовжує regex-парсинг з prose.
- `quality_metrics.priority_tier`: підозрюється як `profitable_pct == 100` (підтверджено на brute_id 12300, BTC-файлі). Tier_1 не відрізняє справжню "Proven Strategy" від "ніколи не йшла в мінус in-sample".
- `recommended_settings_id` (top-level, v7.3): є, але оркестратор його не читає — видобуває settings_id regex-ом з `actionable_guidance` prose.
- Embeddings: 1536-dim `text-embedding-3-small`. `text_builder.py` читає top-level ключі старої схеми (`strategy_overview`, `key_performance_metrics`) — вони відсутні у поточному unified JSON → embeddings будуються майже порожніми (підтверджено через grep).

**Що потрібно (POMDP):**

- Per-regime expected return + risk для кожної стратегії в бібліотеці: E[ROI | regime=R_k] і σ(ROI | regime=R_k) або хоча б MDD per regime.

**Gap:**

1. `regime_performance` (per-regime ROI/fitness/winrate) є лише у 24.9% стратегій і не консьюмується оркестратором. Для 75.1% стратегій per-regime профіль відсутній.
2. `benchmark_periods` баг: дублікати одного інтервалу з різними мітками роблять `compute_strategy_regime_fit` ненадійним. Числа виходять некоректні — alpha по режиму неможливо обчислити.
3. `benchmark` відсутній для 37.7% (6291 стратегій): WB-фільтри та ROI overlay для них не працюють, fallback на aggregate stats.
4. `wb_context` відсутній для 48.8% (8161 стратегій): regime-conditional availability не enforced.
5. Embeddings стають деградованими через schema mismatch у `text_builder.py`: semantic search top-50 потенційно нерелевантний для нових датасетів.
6. `quality_metrics.oos_roi/oos_mdd` є в JSON але не читаються: деградація in-sample → OOS невидима для користувача.
7. `indicators_used` нейминг несумісний між стратегіями (короткі коди vs довгі імена vs не-індикатори "Price", "Volume") — ламає indicator index в `KnowledgeBase.by_indicator`.
8. `priority_tier` підозрюваний як `profitable_pct == 100` без фіксованої формули в JSON — не надійний сигнал якості для POMDP policy.

---

## 4. Policy / decision layer

**Що є:**

- Одна функція `process_query()` (~1500 LOC, `orchestrator.py`): QueryParser → SemanticSearch (top-50, hybrid 0.4×keyword + 0.6×semantic) → filter cascade (9 рівнів) → FactExtractor → GPTSynthesizer.
- 7 значень `intent`: `educational | reliable | best_reliable | find_best | explain | compare | general`. Всі крім `educational` ведуть до одного retrieval шляху.
- GPT-4o-mini, temperature=0.3, max_tokens=200. Один system prompt, 8 правил, завжди вимагає: "Top pick: X% ROI / Y% drawdown". Немає варіативності prompts по intent.
- Режимна фільтрація: `compute_strategy_regime_fit` + `wb_context.regime_risk_flags` (hard drop). Є в коді, але базується на зіпсованих `benchmark_periods`.
- WB personalization: `WBUserProfile` (collateral, risk_preference, max_leverage) впливає на GPT context block, але не на retrieval алгоритм.
- 9-рівневий fallback cascade коли кількість результатів нижча порогу.
- Backtesting config generation: `wb-backtesting-config` endpoint. Не пов'язаний з RAG pipeline.

**Що потрібно (POMDP):**

- Policy `π(a | belief_user, belief_market, strategy_pool)`: вибір дії (яку стратегію рекомендувати, як відповісти, що уточнити) на базі posterior beliefs, а не rule-based filter cascade.
- Belief update: після кожної відповіді оновлювати b_t(s_user) і b_t(s_market).
- Action space: не тільки "яку стратегію показати", але й "задати уточнюче питання", "попередити про ризик", "відмовитись від прогнозу".

**Gap:**

1. Немає belief state. Кожен запит обробляється незалежно. `conversation_history[-4:]` передається в GPT, але не оновлює жодного прихованого стану.
2. Немає policy функції — є filter cascade + GPT prompt. Вибір дії детермінований за intent + порогами, не оптимізований за reward.
3. Intent detection (7 значень) — повністю замінює архетипічний router. Не покриває: `risk_intelligence` (danger score, priority-to-close), `operational_followup` (capital/leverage/stop для вже показаної картки), `forecast_deflection`, `capability_scope`.
4. `danger_score` і `priority_score` не обчислюються і не консьюмуються оркестратором — L4 risk questions повертають strategy cards або generic fallback (підтверджено в CLAUDE_CODE_TASK_SDL_ANSWER_COVERAGE.md).
5. GPT synthesizer — один prompt для всіх типів запитів. Форсує формат "Top pick: X% ROI" навіть коли питання не про вибір стратегії.
6. Немає механізму "відмови від відповіді" при відсутності релевантних даних — є лише 9-рівневий fallback що в кінцевому підсумку повертає щось.
7. Reward функція відсутня. `rating` (-1/0/1) збирається в advisor sessions, але не використовується для оновлення будь-якої моделі.
8. Policy не враховує belief_market: live режим є (RegimeService), але фільтрація по режиму відбувається лише якщо запит містить режимні keywords — не автоматично.

---

## 5. Відомі дефекти поточної системи, що блокують POMDP-шар

Підтверджені дефекти з кодової бази та review-документів:

**Критичні (блокують коректність даних):**

- **D1. `benchmark_periods` дублікати з різними regime-мітками** (04_unified_json_v7_3_review.md, bug A). Один часовий інтервал записується тричі з мітками R1/R2/R3. `compute_strategy_regime_fit` повертає безглузді результати. Блокує побудову per-regime strategy profile.
- **D2. `text_builder.py` читає неіснуючі top-level ключі** (07_factual_description_critical_review.md, П3). Embeddings генеруються з порожніми або мінімальними даними для поточної схеми unified JSON. Блокує semantic search якість.
- **D3. Regex по prose для числових метрик** (07_factual_description_critical_review.md, П2). `actionable_guidance` — list[str]. Orchestrator парсить звідти `best_roi`, `best_fitness`, `profit_factor`, `settings_id` regex-ом. Будь-яка зміна формулювання в генераторі мовчки ламає production.

**Серйозні (знижують якість):**

- **D4. `rag_retriever.py:204` — `fd = data['factual_description']` без `.get()`** (07_factual_description_critical_review.md, П4). KeyError при відсутності поля → runtime crash.
- **D5. `market_context.intervals[].year/.roi_percent/.trend_label` mismatch** (07_factual_description_critical_review.md, П7). `rag_retriever` очікує ці поля, генератор пише `benchmark_periods[].roi/.volatility/.regime`. Поля тихо повертають None.
- **D6. `indicators_used` несумісний нейминг** (04_unified_json_v7_3_review.md, bug H). Короткі коди vs довгі імена vs "Price"/"Volume" в різних стратегіях. `KnowledgeBase.by_indicator` ламає retrieval by indicator.
- **D7. `priority_tier` підозрюється як `profitable_pct == 100`** (04_unified_json_v7_3_review.md, bug I). Tier_1 присвоюється стратегіям з `oos_roi ≈ 0` — пряма дезінформація користувача.
- **D8. `cross_asset_comparison` пишеться для паттерна, не для стратегії** (04_unified_json_v7_3_review.md, bug F). BTC-файл містить "avoid BTC" в описі. Якщо потрапляє в GPT context — self-contradicting evidence.
- **D9. `risk_assessment` шаблон "Set hard stop at X drawdown (1.5× best-case)" при best-case=0** (04_unified_json_v7_3_review.md, bug G). Дає рекомендацію виходити на першій свічці просадки. Опасний текст у production.
- **D10. `impact_score` = range, маркований як "% variance explained"** (07_factual_description_critical_review.md, §1.3). `_gen_parameters()` line 1645: `"explains {impact*100:.0f}% of fitness variance"` — математично некоректно. Якщо `parameter_insights` підключать до retrieval — неправдива статистика попаде в LLM.

**Структурні (блокують POMDP-інтеграцію):**

- **D11. `regime_performance` (top-level v7.3) не читається оркестратором** (блок B). 24.9% стратегій мають per-regime ROI/fitness/winrate, оркестратор їх ігнорує. Основний struct для POMDP strategy profiles недоступний.
- **D12. `recommended_settings_id` не читається оркестратором** (блок B). Видобувається regex-ом з prose замість прямого читання поля.
- **D13. `quality_metrics.oos_roi/oos_mdd/warnings` не читаються оркестратором** (04_unified_json_v7_3_review.md). `OOS_DEGRADATION_VS_INSAMPLE` warning не доходить до користувача.
- **D14. Розбіжність схем між датасетами** (04_unified_json_v7_3_review.md, bug J). dataset_id=15 втрачає `metadata`, `regime_performance`, `factory_catalog_extensions`. Немає специфікації обов'язкових полів для retrieval.
- **D15. Три консюмера unified JSON — три різні схеми без синхронізації** (07_factual_description_critical_review.md, П1). `text_builder`, `orchestrator.py`, `rag_retriever.py` читають різні гілки, немає shared contract.

---

*Тільки підтверджені факти. [UNKNOWN] позначає невирішені питання.*
