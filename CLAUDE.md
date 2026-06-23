# adaptive_aisa — Project Memory

@~/.claude/SYSTEM_PROMPT.md

## Природа проєкту

Дослідницький **генератор розмічених даних** (синтетичний трейдер-харнес). НЕ постійний
сервіс: немає портів, launchd, деплою. Працює пакетно: `config → harness → data → analysis → reports`.
Мета: до приходу живих даних WhiteBIT мати вибірку `(контекст → дія)` для пошуку патернів і
кластеризації користувачів. Деталі — `harness/00_PROJECT_DATA_GENERATOR.md`.

## ⚠️ Machine map (критично для Claude Code)

| Machine | Роль | Claude Code? |
|---|---|---|
| **skufs** (Mac Mini) | робоча: git, прогони, аналіз, БД через WireGuard | **YES — active shell** |
| MacBook Pro | дзеркало для документації | `git pull` only |

- `ssh skufs-mac-mini` і `ssh skufs-vpn` — одна й та сама машина (skufs).
- Доступ до БД (`77.42.77.82`) — через WireGuard-тунель `Home-WG` (10.10.0.0/24), НЕ OpenVPN.
- Робоча копія проєкту: `~/adaptive_aisa/` на skufs (окремо від `~/wbprd_skufs/`).

## ⛔ Заборони (незмінні)

- **GitLab `git.forvest.software` (група `frv`, ID 290) — READ-ONLY для будь-якого AI.**
  Дозволено: clone, pull, читання. ЗАБОРОНЕНО: push, commit, merge, зміни issue/MR.
- Робочий репозиторій проєкту — `github.com/avrich5/adaptive-aisa` (особистий GitHub, не frv).
  Межа: **frv GitLab — тільки читати; avrich5 GitHub — писати сюди.**
- НЕ писати у віддалену БД (тільки SELECT).
- НЕ редагувати `.env`.
- НЕ копіювати чужі дані в репо: `base-states` parquet/режими — зовнішня залежність, не вміст.

## Структура

\`\`\`
adaptive_aisa/
├── CLAUDE.md          ← ця памʼять проєкту
├── README.md          ← точка входу, порядок читання
├── config/            ← персони, осі, набір вікон просадки, пороги мірок (що змінюється між прогонами)
├── harness/           ← генератор рядків-точок + спеки (синтетичний трейдер-харнес)
├── data/              ← датасет точок (git-ignored: parquet, runs)
├── analysis/          ← кластеризація по спостережуваному + пошук патернів
├── reports/           ← вихід: чи пройшла мірка (три мовчання розійшлися?)
├── tasks/             ← ЄДИНА точка читання тасків для Claude Code (всі CLAUDE_CODE / NN_TASK тут)
└── .gitignore
\`\`\`

## Джерела даних (зовнішні залежності, не вміст репо)

- **OHLCV-свічки** — `~/wbprd_skufs/base-states/data/parquet/{whitebit,binance}/` (на skufs — РОБОЧИЙ шлях; у MacBook-дзеркалі шлях інший): 7 активів
  (BTC ETH SOL XRP DOGE BNB ADA), `*_USDT_1d.parquet`, daily, ~1517 рядків
  (2022-04-28 -> 2026-06-22). Колонки: open/high/low/close/volume/quote_volume/trades.
  Це СИРОВИНА, не режими.
- **Режими Base-States** — продукуються pipeline `base-states-dev` ПОВЕРХ цих свічок
  (`pipeline/`, Dockerfile.pipeline), або тягнуться з БД через WireGuard. Готового файла
  режимів немає — режим обчислюється. На skufs звіряти фактичний шлях data/ перед прогоном.
- **Дії користувачів** — `dev.wb_strategies`, `dev.portfolio_action_log` (БД через WireGuard, SELECT).
- **Бібліотека стратегій** — реальна, з БД/міндатасетів. Жодного моку.

## Передумови середовища (звірити на skufs перед прогоном)

- Python на skufs — системний 3.9.6, `uv` не встановлено. Для харнесу створити `.venv`
  (`python3 -m venv` або поставити uv). Зафіксувати рішення в журналі нижче.
- `b2` встановлено (Backblaze, для postflight-бекапу памʼяті) — як у home_services.

## Gates (якість даних перед аналізом)

У дусі GR-007 (no fact without state_id + CI). Перед тим як датасет іде в `analysis/`:
- жодного рядка-точки без `state_id` / `regime`;
- жодної точки з порожнім контекстом;
- прихований вектор НЕ присутній у спостережуваних полях (не витік у те, що піде в кластеризацію);
- мірка успіху задана числом ДО прогону (поріг розрізнюваності), не підганяється під результат.

## Операційна обвязка (preflight / postflight)

Реєструється в **проєктному** `~/adaptive_aisa/.claude/settings.json` (НЕ в глобальному ~/.claude — хуки одного проєкту не забруднюють глобал). Спрацьовують лише для сесій у цій теці:
- **preflight (SessionStart):** git-стан + стан датасету (скільки точок згенеровано, по яких вікнах,
  чи пройшла остання мірка з reports). Щоб сесія бачила, на чому спинилися прогони.
- **postflight (Stop):** бекап `CLAUDE.md` + журналу рішень у `~/.claude/backups/adaptive_aisa/`,
  ротація (останні 10), sync у Backblaze B2.
- Хуки в `hooks/`, зареєстровані в `.claude/settings.json` (проєктний рівень).

## Робочий цикл (порядок)

1. Крок 1 — консенсус-таксономія станів (47 → 8–12). Передумова, ще НЕ зроблено.
2. `tasks/01_TASK_PROJECT_SETUP.md` — git init + remote avrich5/adaptive-aisa.
3. `tasks/02_TASK_HARNESS_BUILD.md` — збірка генератора (шар 1) → таблиця точок.
4. Прогони через набір вікон різних типів → накопичення датасету в `data/`.
5. `analysis/` — кластеризація по спостережуваному + перевірка мірки.
6. Розвилка: мірка пройдена → готувати перехід на живі дані; ні → добрати спостережувані поля.
7. Політика — окремий проєкт ПІСЛЯ розвилки.

---

## Decisions (append-only — не видаляти старі записи)

### 2026-06-23 — проєкт-каркас на skufs
- Створено `~/adaptive_aisa/` на skufs (робоча машина), структура pipeline-стадій.
- Зафіксовано: frv GitLab read-only для AI; робочий репозиторій avrich5/adaptive-aisa (GitHub).
- Природа = генератор даних, не сервіс: відкинуто launchd/порти/health/deploy з образця home_services.
- Одиниця даних — ТОЧКА (атом, таблиця істини); траєкторія — похідне (group by run_id), окремо не зберігається.
- Призначення вибірки: пошук патернів + кластеризація; політика — наступний етап.
- Джерело режимів (parquet vs БД vs pipeline base-states-dev) — резолвити на перших прогонах.
- ВІДКРИТЕ: Python 3.9.6 на skufs, uv нема — рішення по venv до збірки харнесу.

### 2026-06-23 — репозиторій оформлено + обвязка
- Перший push: avrich5/adaptive-aisa, main, коміт da247e4 (52 файли).
- Хуки на ПРОЄКТНОМУ рівні `.claude/settings.json` (глобальний ~/.claude не чіпали).
- Джерело даних уточнено: OHLCV 7 активів × 2 біржі в base-states-dev/data/, режими рахує pipeline.
- Playbook: ~/.claude/NEW_PROJECT_PLAYBOOK.md.
- ВІДКРИТЕ далі: синхронізація MacBook-дзеркала; точка читання tasks для Claude Code; перший код E2E.

### 2026-06-23 — сесію відпрацьовано E2E (нюанси для передачі)
- **Синхронізація машин:** skufs = master (SSH push), MacBook = дзеркало (HTTPS pull,
  `~/adaptive_aisa`, як home_services). Обидві на коміті 1a884c5. Стара
  `~/wbprd_macbook/adaptive_aisa` (без git) — НЕ чіпати, це догіт-залишок.
- **Точка читання тасків:** `tasks/` — ЄДИНА. 01/02_TASK перенесено з harness/ туди.
  harness/ = лише описи (HANDOFF, EXECUTION_ORDER, PROJECT_DATA_GENERATOR, DRAFT).
- **КРИТИЧНИЙ НЮАНС шляху даних:** parquet на skufs лежать у
  `~/wbprd_skufs/base-states/data/parquet/{whitebit,binance}/`, НЕ у wbprd_macbook
  (то був MacBook-шлях, на якому дивився Claude). Канонічний шлях — у `config/data_sources.py`.
- **Перший код E2E пройшов:** `analysis/drawdown_windows.py` читає реальні свічки →
  26 drawdown-вікон по 7 активах → `reports/drawdown_windows.md`. pandas 2.3.3/pyarrow на skufs є.
- **Хуки перевірено вживую:** preflight видає валідний JSON; postflight робить бекап + B2 sync.
- **Наступний крок:** консенсус-таксономія (tasks/CLAUDE_CODE_TASK_CONSENSUS.md) — передумова
  збірки генератора (tasks/02_TASK_HARNESS_BUILD.md).

### 2026-06-23 — ВИПРАВЛЕННЯ моделі даних (свіжість)
- Помилка: записав skufs-шлях як «канонічний», а MacBook як «неправильний». Насправді
  MacBook-дані СВІЖІШІ: 2026-06-22 (1517 свічок) проти skufs 2026-06-02 (1487). Різниця 30 свічок.
- Перший E2E був порахований на СТАРИХ даних. Свіжі parquet скопійовано MacBook -> skufs
  (`scp` у `~/wbprd_skufs/base-states/data/parquet/`), drawdown пораховано наново: 25 вікон.
  BTC underwater-вікно поглибилось 49.5%->51.2%, дно зсунулось 02-05 -> 06-06 (було поза старими даними).
- ПРАВИЛО: parquet оновлюються деінде (pipeline base-states). Перед прогоном звіряти СВІЖІСТЬ
  (`df.index.max()`), не лише наявність файла. Дані застарівають — перевіряти дату, не тільки шлях.
- Відкрите: автоматизувати оновлення parquet на skufs (зараз ручний scp з MacBook-дзеркала).

### 2026-06-23 — ПРАВИЛЬНА модель даних (parquet = вихід сервісу, не файл для копіювання)
- parquet — це ВИХІД base-states pipeline, а не статичний файл. Свіжість забезпечується
  ЗАПУСКОМ сервісу на skufs, а не scp між машинами. MacBook ні до чого (його свіжість випадкова).
- Механізм: `~/wbprd_skufs/base-states` — docker-compose, сервіс `pipeline` (one-shot:
  fetch->classify->output), монтує `./data:/app/data` -> пише parquet у
  `~/wbprd_skufs/base-states/data/parquet/` НА МІСЦІ.
- Команда генерації: `python -m pipeline.main --market all` (entrypoint Dockerfile.pipeline).
- БЛОКЕР зараз: docker ВСТАНОВЛЕНО (/usr/local/bin/docker -> Docker.app), але DAEMON не запущено
  (Docker Desktop не в процесах, сокет ~/.docker/run/docker.sock відсутній). Тобто "docker завис/не
  піднятий", НЕ "docker нема". Підняти Docker Desktop -> compose запрацює. scp 06-22 — КОСТИЛЬ.
- Pipeline хоче python 3.13 (Dockerfile), на skufs системний 3.9.6 -> прямий запуск без docker
  під питанням сумісності.
- РІШЕННЯ: стартувати Docker Desktop на skufs -> `docker compose up pipeline` -> свіжі parquet на місці.
  Venv 3.13 — запасний шлях, якщо docker небажаний. Костиль-scp прибрати після першого compose-прогону.
- Принцип: всі сервіси ~/wbprd_skufs можна підняти локально на skufs; тоді дані генеруються
  свіжими там, де треба. Дані = функція запущених сервісів, не синхронізація файлів.
- УРОК: неінтерактивний `ssh host "which X"` бреше — PATH урізаний, не бачить Docker.app/Homebrew.
  Перевіряти через `ssh host "zsh -lc ..."`. Не робити висновок "X нема" з голого which.

### 2026-06-23 — TASK 01 (PROJECT_SETUP) ЗАКРИТО
- Усі 6 пунктів чек-листа виконано: інвентар, структура, .gitignore, README(точка входу+статус),
  git+remote, _archive перенесено. Внутрішні лінки звірено grep — битих нема (згадки
  synthetic_trader_harness у HANDOFF — історичний текст snapshot, не навігація).
- 62 файли, repo avrich5/adaptive-aisa, обидві машини синхронні.
- 01 — DONE. Наступна за EXECUTION_ORDER: консенсус (tasks/CLAUDE_CODE_TASK_CONSENSUS.md),
  потім збірка генератора (tasks/02_TASK_HARNESS_BUILD.md).

### 2026-06-23 — TASK 02 спеку вичищено від організаційних помилок
- Виправлено в tasks/02_TASK_HARNESS_BUILD.md (зміст-ядро не чіпав):
  - §1 джерело даних: `all_regimes.parquet` НЕ існує -> режими рахує pipeline поверх
    {ASSET}_USDT_1d.parquet; шлях через config/data_sources.py.
  - формат рядка: вкладений -> ПЛОСКИЙ рядок-точка (атом), посилання на PROJECT_DATA_GENERATOR §5.
  - +розділ 7a Інтеграція з проєктом: skufs, config-шляхи, venv/docker, gates перед data/,
    вихід у data/ (git-ignored), таск з tasks/ vs описи в harness/.
  - залежності: all_regimes прибрано, додано посилання на reports/drawdown_windows.md (25 вікон).


### 2026-06-23 — TASK 02 (HARNESS_BUILD) ВИКОНАНО (commit 6b4bf05)
- Реалізовано шар 1 генератора: 7 персон × 5 drawdown-вікон → таблиця рядків-точок.
- Всі файли харнесу в harness/, конфіги в config/. Дані в data/runs/ (git-ignored).
- all_regimes.parquet ІСНУЄ (виявлено в pipeline_output/whitebit/, до 2026-06-03).
  Версія ~20 днів застаріла. Оновлення: Docker Desktop → docker compose up pipeline.
- UNCLASSIFIED (~14% рядків parquet) — явна політика: пропуск в generate_run(), Gate 2 відхиляє.
  R12_REGIME_TRANSITION — включено (valid_regime).
- Параметри персон: DRAFT. Calibrate після consensus_user_states.json.
  Структура не зміниться — тільки числа в config/personas.yaml.
- Smoke test: 7 persona × 5 windows × seed=42 → 430 рядків за ~2с.
- ВІДКРИТЕ: консенсус-таксономія (tasks/CLAUDE_CODE_TASK_CONSENSUS.md) — передумова
  для фінального калібрування меж персон. Data ready (47 states, 5 experts).
- Наступний крок по EXECUTION_ORDER: прогони через набір вікон → накопичення датасету
  (кроки 4-5), потім кластеризація (analysis/).

### 2026-06-23 — TASK 02 (HARNESS_BUILD) ЗАКРИТО + перевірено
- Claude Code зібрав харнес: 11 файлів, коміт 862c8e3. Smoke 7×5×seed42 → 430 рядків ~2с.
- Перевірено на skufs (не на слово):
  - Структура — плоский рядок-точка, усі колонки (мітки/контекст/прихований/action). Відповідає рішенням.
  - Розмаїття дій — усі 12 класів присутні, не схлопнулось. Характери персон різні.
  - ГОЛОВНЕ: три мовчуни молчать з різною інтенсивністю (blind 95 / passive 81 / anxious 36)
    і з різними супутніми діями → "мовчання полісемантичне" відтворюється в даних. Кластеризація зможе.
  - Відтворюваність (рівень A): seed=42 двічі → ідентичні action і hidden vector. Датасет пересоздаваний.
  - Псевдо-баг "46% рассинхрон regime": НЕ баг. Персона реагує на ГРУПУ режиму (bull/bear/range/
    crisis/transition, REGIME_GROUPS), у дані пишеться точний R-код. Маппінг коректний.
- НЮАНС для аналізу: персона вирішує по групі (5), кластеризація піде по точному коду (12).
  Причинність контекст→дія йде через ГРУПУ. Не шукати сигнал у різниці R3 vs R5 — персона її не бачила.
- 02 — DONE. Наступне: analysis/ — кластеризація, перевірка метрики (чи розходяться 3 мовчання).
