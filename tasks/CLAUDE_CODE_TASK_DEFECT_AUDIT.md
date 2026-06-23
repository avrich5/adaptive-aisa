# CLAUDE_CODE_TASK_DEFECT_AUDIT — перевірка стану 15 дефектів (D1–D15)

**Тип:** implementation/audit session (Claude Code). Це ПЕРЕВІРКА стану, не виправлення.
**Ціль:** для кожного з 15 дефектів з `E_gap_analysis.md` §5 встановити поточний статус у коді:
FIXED / PRESENT / PARTIAL / CANNOT_VERIFY. Без правок коду. Вихід — звіт.
**Джерело істини по дефектах:** `adaptive_aisa/E_gap_analysis.md` розділ 5 (D1–D15).
**Контекст покриття:** `adaptive_aisa/B_strategies_coverage.md`, `00_INDEX.md` (SQL-цифри).

---

## Рамка

- НЕ виправляти. Тільки діагностувати і зафіксувати стан. Виправлення — окрема сесія після пріоритизації Андрієм.
- Кожен дефект був підтверджений раніше у конкретному review-документі або grep-ом. Завдання — перевірити, чи він ще присутній СЬОГОДНІ в поточному коді на гілці.
- Дефекти описують стан станом на 2026-06-05. Код міг змінитися. Не довіряти старій мітці — перевіряти на диску/в БД зараз.
- Кожен висновок підкріпити доказом: шлях до файлу + рядок, або SQL-результат, або вивід grep. Без доказу статус = CANNOT_VERIFY.

---

## Репозиторії та де шукати (звірити фактичні шляхи перед стартом)

- `ai-trading-strategy-advisor` — оркестратор: `orchestrator.py`, `rag_retriever.py`, `text_builder` (якщо тут), `generate_embeddings.py`.
- `llm-training-data-miner` — генератор unified JSON: `unified_generator.py`, `text_builder.py`.
- БД `ai_orchestrator`, таблиця `dev.strategies` — для перевірки покриття полів (потрібен доступ; SQL-приклади в `sql_log/`).
- Гілки: перевіряти `development` (true prod), не GitHub-експерименти. Зафіксувати точний commit hash, на якому робиться аудит.

---

## Класифікація статусу (єдина для всіх)

- **FIXED** — дефект усунутий, є доказ (код читає правильне поле / баг даних відсутній).
- **PRESENT** — дефект відтворюється сьогодні, є доказ.
- **PARTIAL** — частково усунутий або усунутий в одному місці з кількох.
- **CANNOT_VERIFY** — нема доступу до файлу/БД/parquet. Вказати, ЩО саме потрібно для перевірки.

---

## Чек-лист по дефектах

### Критичні (блокують коректність даних)

**D1. `benchmark_periods` дублікати з різними regime-мітками.**
Перевірити: чи один часовий інтервал ще пишеться кілька разів з мітками R1/R2/R3.
Де: SQL по `dev.strategies` (приклад підтвердження був на dataset_id=14/15) + читання `compute_strategy_regime_fit` в `orchestrator.py`.
Доказ FIXED: інтервали унікальні per regime АБО generator виправлено (звірити з OQ E3 — чи виправлено в generator v7.3).

**D2. `text_builder.py` читає неіснуючі top-level ключі → порожні embeddings.**
Перевірити: які ключі реально читає `text_builder.py` зараз і чи є вони в поточній схемі unified JSON.
Де: `text_builder.py` (`llm-training-data-miner`), звірити з реальним JSON в `dev.strategies.data`.
Доказ FIXED: ключі, що читаються, присутні в актуальному JSON; embedding-рядок непорожній.

**D3. Regex по prose для числових метрик (`actionable_guidance`).**
Перевірити: чи оркестратор ще парсить `best_roi`/`best_fitness`/`profit_factor`/`settings_id` regex-ом з prose замість читання структурованих полів.
Де: `orchestrator.py` / `rag_retriever.py`, пошук regex навколо `actionable_guidance`.

### Серйозні (знижують якість)

**D4. `rag_retriever.py:204` — `data['factual_description']` без `.get()` → KeyError.**
Перевірити: чи доступ ще без `.get()`; чи рядок ще ~204 (міг зсунутись).
Де: `rag_retriever.py`. Доказ: точний рядок з контекстом.

**D5. `market_context.intervals[].year/.roi_percent/.trend_label` mismatch.**
Перевірити: чи `rag_retriever` ще очікує `year/roi_percent/trend_label`, тоді як generator пише `benchmark_periods[].roi/.volatility/.regime`.
Де: обидва боки — `rag_retriever.py` + `unified_generator.py`.

**D6. `indicators_used` несумісний нейминг (коди vs імена vs "Price"/"Volume").**
Перевірити: чи `KnowledgeBase.by_indicator` ще ламається на різнобої; чи є нормалізація.
Де: код побудови indicator index + вибірка значень `indicators_used` з JSON.

**D7. `priority_tier` як `profitable_pct == 100` (Tier_1 при oos_roi≈0).**
Перевірити: точну формулу присвоєння `priority_tier` в generator (OQ B1/E1).
Де: `unified_generator.py` навколо `priority_tier`. Доказ: рядок з умовою.

**D8. `cross_asset_comparison` пишеться для патерна, не для стратегії ("avoid BTC" у BTC-файлі).**
Перевірити: чи поле ще генерується на рівні патерна; чи потрапляє в GPT-контекст.
Де: generator + місце складання GPT context в оркестраторі.

**D9. `risk_assessment` "stop at 1.5× best-case" при best-case=0 → вихід на першій свічці.**
Перевірити: чи шаблон ще множить best-case без guard на нуль.
Де: `unified_generator.py`, шаблон risk_assessment / `_gen_*`.

**D10. `impact_score` = range, маркований як "% variance explained".**
Перевірити: чи рядок ~1645 `_gen_parameters()` ще пише `"explains {impact*100:.0f}% of fitness variance"`; чи `parameter_insights` підключені до retrieval.
Де: `unified_generator.py`.

### Структурні (блокують POMDP-інтеграцію)

**D11. `regime_performance` (top-level v7.3) не читається оркестратором.**
Перевірити: чи оркестратор тепер читає `regime_performance`; яка частка стратегій його має (було 24.9%).
Де: grep по `regime_performance` в оркестраторі + SQL покриття по `dev.strategies`.

**D12. `recommended_settings_id` не читається (regex з prose).**
Перевірити: чи читається пряме поле тепер, чи ще regex.
Де: `orchestrator.py` / `rag_retriever.py`.

**D13. `quality_metrics.oos_roi/oos_mdd/warnings` не читаються.**
Перевірити: чи `OOS_DEGRADATION_VS_INSAMPLE` тепер доходить до відповіді.
Де: оркестратор, місце складання фактів/відповіді.

**D14. Розбіжність схем між датасетами (dataset_id=15 втрачає metadata/regime_performance/factory_catalog_extensions).**
Перевірити: чи є специфікація обов'язкових полів; поточний розподіл відсутніх блоків по dataset_id.
Де: SQL по `dev.strategies` group by dataset_id.

**D15. Три консюмери unified JSON — три схеми без shared contract.**
Перевірити: чи зʼявився спільний контракт/схема для `text_builder` + `orchestrator.py` + `rag_retriever.py`.
Де: пошук спільного schema-модуля; якщо нема — статус PRESENT.

---

## Метод (для кожного дефекту)

1. Відкрити вказаний файл, знайти релевантний код (grep по ключових іменах вище).
2. Для дефектів даних — SQL до `dev.strategies` або читання реального JSON-рядка, не лише код.
3. Зафіксувати: статус (FIXED/PRESENT/PARTIAL/CANNOT_VERIFY) + доказ (шлях:рядок або SQL-вивід).
4. Якщо рядок зсунувся або файл перейменовано — записати новий шлях.

---

## Формат звіту (створити `adaptive_aisa/DEFECT_AUDIT_REPORT.md`)

Шапка: дата, repo, гілка, commit hash аудиту.

Таблиця:

| ID | Статус | Доказ (файл:рядок / SQL) | Нотатка |
|----|--------|--------------------------|---------|
| D1 | PRESENT/FIXED/... | ... | ... |

Підсумок: скільки FIXED / PRESENT / PARTIAL / CANNOT_VERIFY; які з PRESENT блокують що
(D1, D11 раніше марковані як блокери POMDP-шару); список CANNOT_VERIFY з тим, що потрібно для перевірки.

---

## Що НЕ робити

- НЕ виправляти жоден дефект у цій сесії.
- НЕ чіпати дані в БД (тільки SELECT).
- НЕ робити записів у віддалену БД.
- НЕ оновлювати `E_gap_analysis.md` — він джерело істини по опису; статус іде в окремий звіт.
- НЕ довіряти старим міткам — перевіряти стан на поточному коміті.
