# POMDP Data Collection — Index

**Дата:** 2026-06-05
**Статус:** інвентаризація завершена + наративний план для людини

---

## 👉 START HERE

[**00_CONCEPT.md**](00_CONCEPT.md) — головний документ для розуміння задуму: цільова функція, модель спостережуваності, роадмап (фази 0-3). Далі [**00_ADAPTIVE_ANSWER_CONCEPT.md**](00_ADAPTIVE_ANSWER_CONCEPT.md) — три осі адаптації відповіді + Pareto-межа. Інші файли — технічна деталізація. (Раніше тут був `00_HUMAN_NARRATIVE.md` — він став `00_CONCEPT.md`.)

---

## Документи інвентаризації

| Файл | Зміст |
|------|-------|
| [A_current_orchestrator.md](A_current_orchestrator.md) | Поточний оркестратор: endpoints, parsing, semantic search, synthesis, user state |
| [B_strategies_coverage.md](B_strategies_coverage.md) | Unified JSON schema (v7.3) + SQL-покриття 16709 стратегій по ключових полях |
| [C_market_regimes.md](C_market_regimes.md) | Режимна модель: алгоритм, 12 режимів, per-asset vs global, transition matrix, latency |
| [D_user_observations.md](D_user_observations.md) | Всі джерела даних про користувача: чат, WB-контекст, портфель, логи |
| [E_gap_analysis.md](E_gap_analysis.md) | Gap analysis A+B+C+D: що є vs що потрібно для POMDP; 15 підтверджених дефектів |
| [F_templates_ops_inventory.md](F_templates_ops_inventory.md) | NEW — інвентаризація profitradar-templates-ops |
| [G_market_regime_table_source.md](G_market_regime_table_source.md) | **NEW** — як насправді формується BY MARKET REGIME таблиця в Detail view. Spoiler: on-the-fly, кеш-таблиця порожня |
| [H_expert_prompt_user_states.md](H_expert_prompt_user_states.md) | **NEW** — промпт для 3-5 експертів (LLM/люди) на визначення 8-12 User States та їх специфіки для WhiteBIT |

## Ключове доповнення з блоку G (виправляє блок F)

`dashboard_strategy_regimes` — порожня. Strategy×Regime матриця **не зберігається ніде**. Per-regime таблиця в Detail view рахується на льоту:

- endpoint `GET /backtest-run/{bt_run_id}/regime-performance`
- читає `backtest_trades` для конкретного run
- HTTP-кол до `base-states /api/history_by_asset` для отримання щоденного режиму по символу
- агрегує в пам'яті, повертає JSON, не пише в кеш

Для POMDP-policy це неприйнятно (1670 round-trips на ranking). Рекомендація: написати `bg_sync_regimes` background-task за аналогією з `bg_sync_metrics`. Алгоритм існує, схема таблиці існує, оцінка — 1-2 дні розробки.

## Допоміжні файли

| Файл | Зміст |
|------|-------|
| [_archive/00_REPOS_SYNC.md](_archive/00_REPOS_SYNC.md) | git pull лог 2026-06-05 (архів) |
| [00_OPEN_QUESTIONS.md](00_OPEN_QUESTIONS.md) | Всі [UNKNOWN] позначки з вказівкою як розв'язати |
| [sql_log/](sql_log/) | SQL-запити B1–B4 і їхні результати (dev.strategies coverage) |
| [scripts/](scripts/) | Скрипти для читання parquet/JSON (якщо генерувалися) |

---

## Ключові цифри (з блоку B, SQL-верифіковані)

| Метрика | Значення |
|---------|---------|
| Всього стратегій у dev.strategies | 16709 |
| З unified JSON `data` | 16709 (100%) |
| З `benchmark` (overlay для оркестратора) | 10418 (62.3%) |
| З `wb_context` (regime risk flags) | 8548 (51.2%) |
| З `regime_performance` top-level (POMDP target) | 4161 (24.9%) |
| З `benchmark_periods` в `market_context` | 16488 (98.7%) |

## Критичні знахідки для POMDP

1. `regime_performance` — єдиний per-regime struct — є у 24.9% і **не читається** оркестратором.
2. `benchmark_periods` баг (дублікати з різними мітками) робить поточний regime-fit cascade ненадійним.
3. Embeddings деградовані через schema mismatch у `text_builder.py`.
4. User state відсутній цілком у WB-flow. `user_id` опційний.
5. 15 підтверджених дефектів (D1–D15) у E_gap_analysis.md; D1 і D11 блокують побудову POMDP-шару.
