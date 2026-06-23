# Repos Sync Log — 2026-06-05

| Repo | Branch | HEAD after pull | Changes pulled |
|------|--------|----------------|----------------|
| `ai-trading-strategy-advisor` | development | a6a3709 | Yes — new wb test + WbStrategyCardView + preview.ts |
| `base-states` | dev | 4ff792d | Already up to date |
| `llm-training-data-miner` | main | 13172cf | Already up to date |
| `profitradar` | main | 195b0ed | Yes — StrategyResults.tsx + api.ts tweaks |
| `profitradar-api` | main | 741d0bb | Yes — migrations 019 wb_strategies + test_wb_schemas.py |
| `profitradar-templates-ops` | (not pulled — added retroactively 2026-06-05) | — | Read-only inspection only |
| `signal-emulator` | main | c9c15e6 | Yes — removed helm values.yaml, added mock-indicators |

Local changes in repos: none detected (all clean pulls).

**Correction (2026-06-05):** `profitradar-templates-ops` was originally marked "not relevant" — incorrect. Andriy flagged it as the repo that powers the dashboard screenshots (Catalog + Detail views with per-regime tables). Added to inventory in B_strategies_coverage.md and A_current_orchestrator.md. Should be `git pull`ed at next sync pass.

Repos still not pulled (confirmed not relevant): scalping-pnl, scalping-ui, shark-bot, shark-monitoring, inc-analytics, indicators-basic, strategy_factory.
