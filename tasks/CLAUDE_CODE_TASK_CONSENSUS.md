# TASK: Consensus User-States taxonomy from expert submissions

**Owner:** Claude Code
**Dir:** `~/wbprd_macbook/adaptive_aisa/`
**Context:** read first — `00_CONCEPT.md` (concept + roadmap; раніше називався `00_HUMAN_NARRATIVE.md`), `H_expert_prompt_user_states.md` (schema + rules), `D_user_observations.md` (which server-context signals actually exist).

## Что уже сделано (не переделывать)
`scripts/consolidate_experts.py` уже:
- загрузил `experts/*.json`, сгруппировал части по `submission_id`, смерджил;
- провалидировал по правилам H;
- записал `personas/_merged/<expert>.json`, `personas/_report/validation_report.md`,
  `personas/_report/all_states_flat.json`.

5 валидных экспертов: deepseek, gemini-1.5-pro, gpt-5, grok, claude-opus-4-7.
47 состояний суммарно. `experts/invalid/mistral_*` — исключён (битый формат).

Known data defects (зафиксированы в отчёте, не блокеры консенсуса):
- deepseek: traffic_share сумма 84, не 100.
- grok: passive_holder имеет 4 typical_questions; две строки матрицы суммируются в 95.

## Задача (это и есть работа Claude Code — семантический слой)

1. **Кластеризация эквивалентных состояний** через `all_states_flat.json`.
   Сматчить состояния-синонимы разных экспертов в один консенсус-стан.
   Пример очевидного кластера: `panic_position_holder` ≈ `panic_holder`
   ≈ `loss_panicker` ≈ `angry_liquidated_complainer`(?). Решай по `one_liner` +
   `typical_server_context` (positions_pnl_state, has_open_positions) +
   `emotional_tone`, НЕ по похожести строки id.
   - Для каждого кластера: сколько экспертов его назвали (support N/5).
   - Состояния, названные только 1 экспертом — long tail, помечай `support: 1`.

2. **Сформировать консенсус-таксономию из 8-12 User States.**
   Критерии включения: support ≥ 2 ИЛИ (support=1 И покрывает реальный
   серверный сигнал из D, который иначе не покрыт). Обязательно ≥1 неторговый стан
   (флуд/тест/жалоба) — этого требует H.
   Для каждого консенсус-стана:
   - канонический `id` (snake_case), `one_liner`;
   - `expected_traffic_share_pct` — усреднить по экспертам кластера, потом
     ОТНОРМИРОВАТЬ так чтобы сумма по всем стейтам = 100;
   - слить `behavioral_patterns`, `typical_questions` (дедуп, оставить 5-8 самых
     характерных, сохранить реалистичный «грязный» язык — это требование H п.4),
     `post_response_actions` (усреднить вероятности, перенормировать к 100);
   - `typical_server_context` — пересечение/объединение, согласовать с тем что
     РЕАЛЬНО есть в D (balances, risk_preference, max_leverage, active_strategies,
     positions PnL). Не выдумывать поля которых нет в payload WB.
   - `source_experts`: список id-экспертов и их исходных state id (трассируемость).

3. **Построить консенсус `transition_matrix`** N×N по новым каноническим id,
   строки суммируются в 100. Базируй на исходных матрицах экспертов (мапь старые
   id→новые, усредняй, перенормируй). Где данных нет — 0, но self-loop правдоподобный.

4. **Свести метаданные**: объединить `questions_for_whitebit_team` (дедуп),
   `classification_risks` (особенно пары состояний которые трудно различить —
   это прямой риск для классификатора belief), `edge_cases_not_covered`.

## Выходные файлы
- `personas/consensus_user_states.json` — финальная таксономия (та же схема что в H:
  `states[]` + `transition_matrix` + сведённые метаданные + `meta.consensus_from`).
- `personas/consensus_report.md` — для человека: таблица кластеров с support N/5,
  что вошло/не вошло и почему, нормализации (какие суммы правились), открытые
  расхождения между экспертами, топ classification_risks.

## Guardrails
- Это вход для симулятора (00_CONCEPT «холодный старт»), НЕ прод-классификатор.
  Поведенческие параметры — генеративные семена персон.
- НЕ изобретать серверные сигналы сверх тех что в D. belief можно строить только
  по реально доступным полям `wb_chat_history.system_context`.
- Не «причёсывать» язык typical_questions в правильный английский — H требует
  сохранять фрагменты/опечатки/мат/смесь языков.
- Сохранять трассируемость: из какого экспертского стана пришёл каждый консенсус-стан.
- Никаких записей в БД, никаких сетевых вызовов. Только файлы в `personas/`.
- В конце — короткий вывод в чат: сколько кластеров, сколько финальных стейтов,
  какие расхождения остались на ревью Андрею.
