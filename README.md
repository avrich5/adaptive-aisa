# adaptive-aisa

Синтетичний трейдер-харнес як **генератор розмічених даних** для пошуку поведінкових
патернів і кластеризації користувачів ProfitRadar / WhiteBIT. Scenario-tool, не предиктор.

## Порядок читання
1. `CLAUDE.md` — памʼять проєкту, machine map, заборони, gates, цикл.
2. `harness/HANDOFF.md` → `harness/00_EXECUTION_ORDER.md` — звідки стартувати.
3. `harness/00_PROJECT_DATA_GENERATOR.md` — зонтична спека: нащо і що на виході.
4. `concept/00_CONCEPT.md` — цільова функція (утримана комісія), модель спостережуваності.
5. `inventory/E_gap_analysis.md` — дефекти/обмеження прод-даних.

## Структура
- `config/` — персони, осі, набір вікон просадки, пороги мірок.
- `harness/` — генератор рядків-точок + спеки.
- `data/` — датасет (git-ignored).
- `analysis/` — кластеризація + пошук патернів.
- `reports/` — результати мірок.
- `concept/`, `inventory/`, `personas/`, `experts/`, `sql_log/`, `scripts/` — аналітична база.
- `tasks/` — спеки для Claude Code.

## Межі
- frv GitLab (`git.forvest.software`) — **READ-ONLY**. Писати тільки в `avrich5/adaptive-aisa`.
- Робоча машина — skufs. MacBook — дзеркало.
- Дані Base-States / WB — зовнішня залежність, у репо не копіюються.
