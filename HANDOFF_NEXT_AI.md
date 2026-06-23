# HANDOFF_NEXT_AI — стан проєкту adaptive_aisa для наступної AI-сесії

Прочитати ПЕРШИМ, потім `CLAUDE.md` (журнал рішень — авторитетний).

## Що це
Синтетичний трейдер-харнес = генератор розмічених даних. Прогоняє 7 персон через
історичні drawdown-вікна, пише плоскі рядки-точки `(контекст → прихований_вектор → дія)`.
Мета: знайти патерн silent churn і кластеризувати користувачів ДО роботи з живими даними WhiteBIT.
Scenario-tool, НЕ предиктор. Прихований вектор живе тільки в харнесі.

## Машини (критично)
- **skufs** (`ssh skufs-mac-mini` = `ssh skufs-vpn`) — робоча: git master, прогони, дані, БД через WireGuard.
- **MacBook** — дзеркало (`~/adaptive_aisa`, git pull по HTTPS). НЕ робоча.
- УВАГА: Desktop Commander виконується на MacBook. Файли правити на skufs через ssh.
  Після правок на skufs зеркало бачить їх лише після `git pull`. read_file з MacBook показує СТАРЕ.
- УВАГА: `ssh host "which X"` бреше (урізаний PATH). Перевіряти через `ssh host "zsh -lc ..."`.

## Межі (незмінні)
- frv GitLab (`git.forvest.software`, ID 290) — READ-ONLY для AI. Писати тільки в avrich5/adaptive-aisa (GitHub).
- НЕ писати в БД (тільки SELECT). НЕ редагувати .env. Дані не копіювати в репо.

## Зроблено
- TASK 01 (project setup) — DONE. Репо оформлено, машини синхронні, _archive перенесено.
- TASK 02 (harness build) — DONE. 11 файлів (коміт 862c8e3). Перевірено: структура, розмаїття дій,
  відтворюваність (seed), три мовчання різні. Smoke 430 рядків.
- Обвязка: хуки preflight/postflight у ПРОЄКТНОМУ `.claude/settings.json` (не глобал). B2 backup.
- Перший E2E: `analysis/drawdown_windows.py` → 25 вікон у `reports/`.

## Дані (модель — важливо)
- parquet = ВИХІД pipeline base-states, не статичний файл. Свіжість = ЗАПУСК pipeline, не scp.
- Сировина (OHLCV): `~/wbprd_skufs/base-states/data/parquet/{whitebit,binance}/{ASSET}_USDT_1d.parquet`.
- Режими (для харнесу): `~/wbprd_skufs/base-states/data/pipeline_output/whitebit/all_regimes.parquet`
  (OHLCV + regime R1-R12 + фічі). Шлях у `config/data_sources.py` — не хардкодити.
- УВАГА свіжість: all_regimes застарілий ~на 20 днів (до 06-03). Перед фінальними прогонами:
  Docker Desktop на skufs (встановлено, демон не піднятий) → `docker compose up pipeline` у base-states.
- UNCLASSIFIED (~14% рядків) — політика: пропускаються генератором, Gate 2 документує.

## Відкрите (наступні кроки за пріоритетом)
1. **analysis/ — кластеризація.** Головна метрика проєкту: чи розходяться 3 мовчання
   (anxious/blind/passive) у різні кластери по СПОСТЕРЕЖУВАНОМУ (без прихованого вектора).
   Поріг розрізнюваності задати ДО прогону. Це розвилка: пройде → дані придатні; ні → добрати поля.
2. **Консенсус** (`tasks/CLAUDE_CODE_TASK_CONSENSUS.md`) — 47 станів → 8-12 канонічних.
   Дані є (`personas/`, 47 станів), `consensus_user_states.json` відсутній. Після — оновити
   числа в `config/personas.yaml` БЕЗ змін коду. Передумова фінальних меж персон.
3. **Свіжі дані** — підняти pipeline (п. вище), перерахувати вікна (btc_underwater зміниться).
4. **Політика** — окремий етап ПІСЛЯ кластеризації. Не зараз.

## Нюанс аналізу (не баг)
Персона вирішує по ГРУПІ режиму (5: bull/bear/range/crisis/transition), у дані пишеться точний
R-код (12). Причинність контекст→дія йде через групу. Не шукати сигнал у різниці R3 vs R5.

## Структура
`config/` (джерела даних, персони, вікна) · `harness/` (генератор + описи) · `analysis/` ·
`data/runs/` (вихід, git-ignored) · `reports/` · `tasks/` (ЄДИНА точка тасків Claude Code) ·
`concept/ inventory/ personas/ experts/ sql_log/ scripts/ _archive/` (аналітична база).
