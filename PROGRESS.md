# PROGRESS — стан проєкту (єдине джерело «де ми»)

Оновлюється CC по одному рядку за сесію. Статус: ✅ DONE | 🔄 IN PROGRESS | ⏳ PENDING | ❌ BLOCKED.

| Етап | Критерій DONE (бінарний) | Статус | Дата | Доказ |
|---|---|---|---|---|
| TASK 01 — Project Setup | Структура, git, remote, README | ✅ DONE | 2026-06-23 | commit da247e4 |
| TASK 02 — Harness Build шар 1 | 7 персон × 5 вікон → 430 рядків, seed відтворюваність | ✅ DONE | 2026-06-23 | commit 862c8e3 |
| P1 — per_regime_display аудит | Формула зафіксована по коду, крива ідентифікована | ✅ DONE | 2026-06-24 | GROUNDTRUTH.md |
| P2 — STOP_TEST уточнення | Append-only запис у CLAUDE.md | ✅ DONE | 2026-06-24 | CLAUDE.md |
| Інфра контролю | PROGRESS + CHECKLIST + GROUNDTRUTH + SESSION_REPORT_TEMPLATE | ✅ DONE | 2026-06-24 | цей файл |
| TASK 03 — Intent Router | ≥80% відповідей у правильній формі на 20 frozen Q | ⏳ PENDING | — | — |
| TASK 05 — Harness шар 2 (цикл) | qpnls як джерело + оркестратор + trust оновлення | ⏳ PENDING | — | — |
| TASK 04 Gate A | trust-динаміка змістовна (4 перевірки пройшли) | ⏳ PENDING | — | — |
| TASK 04 Gate B | різні причини розрізнювані (кластеризація) | ⏳ PENDING | — | — |
| Демо для Dmitriy | цикл advisor↔persona↔trust live з qpnls | ⏳ PENDING | — | — |

**Поточний блокер:** TASK 05 не почато — без qpnls groundtruth-звірка хибна (GROUNDTRUTH.md §5).
**Наступний крок:** TASK 03 (intent-router, незалежна лінія) або TASK 05 крок 1 (доступ до qpnls).
