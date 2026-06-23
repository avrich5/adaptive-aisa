# DEFECT_AUDIT_REPORT — D1–D15 (revised)

**Дата аудиту:** 2026-06-22  
**Аудитор:** Claude Code (read-only, без правок)  
**Ревізія:** після перечитання production code path — false positive-и переоцінені

| Репо | Гілка | Commit |
|------|-------|--------|
| `ai-trading-strategy-advisor` | `development` | `66fffab` |
| `llm-training-data-miner` | `main` | `0e5a044` |

---

## Таблиця результатів

| ID | Статус | Вердикт | Доказ (файл:рядок) | Нотатка |
|----|--------|---------|-------------------|---------|
| D1 | **FIXED** | — | `unified_generator.py:3192–3237` | `_apply_canonical_benchmark_regimes` — `seen_signatures` set дедуплікує. |
| D2 | **MINER** | Не стосується оркестратора | `text_builder.py:38–44` | Майнер переробляється. Поки що — порожні embeddings у старих стратегіях. |
| D3 | **REAL** | Регекс на prose для `settings_id` та KPI | `benchmark_kpis.py` + `unified_extract.py:10–21` | Для стратегій без `benchmark`-колонки: ROI/fitness/profit_factor беруться regex-ом. При малформованому рядку — нулі, стратегія відфільтровується. `settings_id` — завжди regex, немає колонки-fallback. |
| D4 | **FALSE POSITIVE** | Dead code path | `rag_retriever.py:190–193` | `_format_context()` викликається тільки з `retrieve()`, яка не викликається з оркестратора взагалі. Баг реальний, але недосяжний. |
| D5 | **FALSE POSITIVE** | Dead code path | `rag_retriever.py:231–237` | Та сама `retrieve()` — не в production path. |
| D6 | **FALSE POSITIVE** | Оркестратор консистентний | `knowledge_base.py:129, 157` | Всі 8+ call sites читають `indicators_used` однаково через `.get()`. Порожній list при відсутності = no crash, тільки нижче в ранкінгу. Якщо є — miner-side issue. |
| D7 | **FIXED** | — | `unified_generator.py:2981–2989` | Tier_1 вимагає `avg_roi >= 10`. Одного `profitable_pct == 100` недостатньо. |
| D8 | **PARTIAL** | Є в `ask-wb`, нема в `/ask` | `app/wb/cross_asset.py:128`; `orchestrator.py:1131` | `cross_asset_comparison` читається тільки для WB peer cards (`endpoint_label == "ask-wb"`). В головному chat-шляху ігнорується. |
| D9 | **MINER** | Не стосується оркестратора | `unified_generator.py:2874` | `else 21` guard є. Семантично невірно, але майнер переробляється. |
| D10 | **FALSE POSITIVE** | Поле ніколи не доходить до оркестратора | `unified_generator.py:2126` | `parameter_insights` не читається ніде в `app/orchestrator/`. GPT ніколи не бачить це поле. Mislabeling без ефекту. |
| D11 | **FALSE POSITIVE** | Дані є — з `benchmark_periods` | `strategy_regime_fit.py:85–86` | `compute_strategy_regime_fit()` читає `market_context.benchmark_periods` (не `factual_description.regime_performance`). Дані доходять до карток через `regime_fit_to_api_dict()` на `orchestrator.py:1040–1043`. |
| D12 | **REAL** | Той самий regex, що D3 | `unified_extract.py:10–21`; `orchestrator.py:654–658, 1214` | `settings_id` — завжди через regex, прямого читання поля нема. При малформованому рядку `strategy_id = None`, картка без action button. |
| D13 | **REAL** | `oos_roi`/`oos_mdd` не доходять до GPT | Нуль hits для `oos_roi`, `oos_mdd` в `orchestrator/` | `quality_metrics` читається тільки для `priority_tier`. GPT синтезує відповідь без OOS-даних. |
| D14 | **CANNOT_VERIFY** | Потрібен SQL | Нема schema-validation в miner | Потрібен `SELECT dataset_id, sum(...) FROM dev.strategies GROUP BY dataset_id` |
| D15 | **REAL** | Структурний, silent degradation | Нема `unified_schema.py` або аналогу | Будь-яке перейменування поля в miner → тихий None в оркестраторі без логу. |

---

## Реальні проблеми оркестратора — приклади питань

### D3 / D12 — Regex для `settings_id` і KPI з prose

**Питання:** "Покажи найкращі ETH стратегії з RSI"

**Що йде не так:** Якщо miner генерує `actionable_guidance[0]` без шаблонного рядка `"settings_id N"` (наприклад, "Use configuration #2964"), `extract_recommended_settings_id` повертає `None`. `_build_strategy_id` будує `strategy_id = None`. Картка з`являється у відповіді, але кнопка "Activate" на WB-фронтенді не працює — тихо, без помилки.

Паралельно: для стратегій без `benchmark`-колонки `parse_guidance_kpis()` regex-парсить ROI/fitness. Якщо формат рядка змінився — нулі. Фільтр `avg_roi > 0` в `rag_searcher.py:360` прибирає стратегію з результатів. Вона зникає тихо.

---

### D13 — `oos_roi`/`oos_mdd` не в GPT context

**Питання:** "Чи витримує ця SOL стратегія на out-of-sample периодах?"

**Що йде не так:** GPT не має OOS-даних у контексті. У кращому випадку відмовляється відповідати конкретними цифрами. У гіршому — видає in-sample ROI як ніби це валідований результат. Користувач не бачить сигналу, що OOS-метрика взагалі існує або відрізняється.

---

### D15 — Нема shared contract (silent degradation)

**Питання:** "Топ BTC стратегії з високим win rate"

**Що йде не так:** Якщо miner перейменовує `aggregate_stats.avg_win_rate` → `aggregate_stats.win_rate_avg`, `resolve_win_rate_pct()` отримує `None`, падає через всі три fallback, повертає `None`. Картки в відповіді — без `win_rate`. Фронтенд показує прочерк. Лог нічого не фіксує — причина невидима.

---

## Підсумок (revised)

| Статус | К-сть | ID |
|--------|-------|----|
| FIXED | 2 | D1, D7 |
| REAL (оркестратор) | 4 | D3, D12, D13, D15 |
| PARTIAL (оркестратор) | 1 | D8 |
| FALSE POSITIVE | 5 | D4, D5, D6, D10, D11 |
| MINER (не стосується) | 2 | D2, D9 |
| CANNOT_VERIFY | 1 | D14 |

**Пріоритет для фікса:**
1. D3/D12 — regex для `settings_id`: картки без action button, тихе зникнення стратегій
2. D13 — OOS-дані не в GPT: якісно невірні відповіді на питання про надійність стратегій
3. D15 — відсутній contract: будь-яка зміна в miner → тихий регрес в оркестраторі

---

## CANNOT_VERIFY (D14) — що потрібно

```sql
SELECT
  dataset_id,
  count(*) AS total,
  sum(CASE WHEN data ? 'regime_performance' THEN 1 ELSE 0 END) AS has_regime_perf,
  sum(CASE WHEN data ? 'metadata' THEN 1 ELSE 0 END) AS has_metadata,
  sum(CASE WHEN data #>> '{factory_catalog_extensions}' IS NOT NULL THEN 1 ELSE 0 END) AS has_catalog_ext
FROM dev.strategies
GROUP BY dataset_id
ORDER BY dataset_id;
```
