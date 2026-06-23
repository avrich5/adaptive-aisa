# Промпт для експертів: категорії та поведінкові патерни користувачів WhiteBIT

**Призначення.** Отримати від 3-5 незалежних експертів (LLM або людей) структуровану таксономію User States для AI Strategy Advisor на WhiteBIT. Результат — сирий JSON, який потім склеює і валідує Claude Code.

**Кому давати паралельно.**
- Claude Opus / Sonnet (2-3 незалежні сесії з чистим контекстом)
- GPT-5 / o3
- DeepSeek
- Якщо є — продакт або трейдер WhiteBIT (людина — пише той самий JSON руками або диктує LLM)

**Не показувати відповіді одного експерта іншому.** Не редагувати промпт між експертами.

## Як зберігати відповіді

Один експерт = одна директорія `personas/raw/expert_<name>/`. Усередині — або один файл `part_1_of_1.json`, або кілька (`part_1_of_2.json`, `part_2_of_2.json` тощо) відповідно до того як експерт розбив відповідь.

Назви директорій: `expert_claude_opus`, `expert_gpt5`, `expert_deepseek`, `expert_human_andriy`.

Claude Code потім сам:
- зчитує всі частини одного експерта по спільному `submission_id` в meta
- перевіряє `part_number` / `total_parts` на повноту
- мерджить частини в один логічний об'єкт
- валідує (суми ймовірностей, посилання transition_matrix, наявність required-полів)
- зводить кілька експертів у консенсус-таксономію

Якщо експерт схалтурив (відсутня частина, неправильний submission_id, невалідний JSON) — Claude Code це побачить і доповість що саме переробити.

Все що нижче — копіювати в новий чат експерту цілком, від лінії до лінії.

---
---

Ти експерт з продуктової аналітики криптобірж з 10+ років досвіду (Binance, Bybit, OKX, WhiteBIT). Розумієш поведінкові патерни розкових типів трейдерів.

Тебе наймають для підготовки даних до проекту: **AI-радник у чаті на WhiteBIT**, який рекомендує торгові стратегії з бібліотеки бектестованих алгоритмів. На кожне повідомлення радник бачить серверний контекст: баланс USDT, відкриті позиції з PnL, ризик-профіль (low/medium/risky), макс. плече, активні стратегії. Радник повертає текст + картки стратегій. Користувач може: новий запит, клік на картку, активувати стратегію, ігнорувати, піти.

## Завдання

Опиши **8-12 типів користувачів** (User States) і поверни **один валідний JSON-об'єкт** строго за схемою нижче. Без вступу, без коментарів навколо JSON, без markdown-обгортки ` ```json `. Тільки JSON від `{` до `}`.

User State — це **функціональний стан користувача в момент звернення**, не демографія. Один реальний користувач за тиждень побуває в 5 різних станах. Нас цікавлять стани.

## JSON-схема (обов'язково дотримуватись)

Кожен JSON-об'єкт (єдиний або частина) починається з **meta-блоку**. Структура meta однакова, навіть якщо весь ответ у одній частині.

```
{
  "meta": {
    "expert_id": "<твоє ім'я моделі або псевдо, наприклад 'claude-opus-4-7'>",
    "submission_id": "<будь-який унікальний рядок, однаковий для всіх частин цієї відповіді, напр. 'opus_run_001'>",
    "schema_version": "1.0",
    "part_number": <число 1, 2 або 3>,
    "total_parts": <число 1, 2 або 3>,
    "content_type": "<full | states | matrix | metadata | states_and_matrix>"
  },
  ... (далі payload відповідно до content_type, див. нижче)
}
```

**Payload залежно від `content_type`:**

- `full` — повна відповідь в одній частині. Payload містить ВСІ поля: `states`, `transition_matrix`, `edge_cases_not_covered`, `questions_for_whitebit_team`, `classification_risks`, `confidence_self_assessment`, `self_check`.
- `states` — тільки масив `states` (для розбиття 1 з 3 або 1 з 2).
- `matrix` — тільки `transition_matrix` (для розбиття 2 з 3).
- `metadata` — `edge_cases_not_covered` + `questions_for_whitebit_team` + `classification_risks` + `confidence_self_assessment` + `self_check` (фінальна частина при розбитті).
- `states_and_matrix` — `states` + `transition_matrix` разом (для розбиття 1 з 2).

**Дозволені варіанти розбиття:**

| total_parts | part 1 | part 2 | part 3 |
|---|---|---|---|
| 1 | full | — | — |
| 2 | states_and_matrix | metadata | — |
| 3 | states | matrix | metadata |

**Заборонено:** інші комбінації, довільне дроблення states по кілька штук, переплутаний порядок частин.

## Повна структура payload (з усіма полями)

Кожне з цих полів зявляється в JSON відповідно до `content_type`:

```
"states": [
    {
      "id": "<snake_case_unique>",
      "one_liner": "<одна фраза що користувач намагається зробити>",
      "expected_traffic_share_pct": <число 1-50>,
      "typical_server_context": {
        "balance_usdt_range": [<min>, <max>],
        "has_open_positions": "<true | false | sometimes>",
        "positions_pnl_state": "<profit | loss | mixed | n/a>",
        "risk_preference": ["<low|medium|risky>", ...],
        "has_active_strategies": "<true | false | sometimes>",
        "active_strategies_count_range": [<min>, <max>]
      },
      "emotional_tone": "<anxiety|curiosity|greed|apathy|frustration|calculation|confusion|excitement>",
      "behavioral_patterns": {
        "typing_style": "<terse|verbose|fragments|shouting|polite>",
        "typo_frequency": "<none|rare|frequent|heavy>",
        "language_mix": "<ru|en|uk|mixed_ru_en|mixed_uk_ru>",
        "profanity": "<none|rare|frequent>",
        "avg_messages_per_session": <число>,
        "avg_session_duration_minutes": <число>,
        "repeat_rate_pct": <0-100>
      },
      "typical_questions": [
        "<5-8 формулювань реальною мовою>",
        "..."
      ],
      "post_response_actions": [
        {"action": "<click_card|activate_strategy|ask_followup|ignore|leave_chat|complain>", "probability_pct": <число>},
        ...
      ],
      "state_transitions": [
        {"to": "<id іншого стану>", "trigger": "<короткий опис>", "probability_pct": <число>},
        ...
      ]
    }
  ],
  "transition_matrix": {
    "<state_id_1>": {"<state_id_1>": <число>, "<state_id_2>": <число>, ...},
    "<state_id_2>": {...}
  },
  "edge_cases_not_covered": [
    "<граничний випадок який не вмістився в основні стани>",
    "..."
  ],
  "questions_for_whitebit_team": [
    "<3-5 питань що уточнять картину>",
    "..."
  ],
  "classification_risks": [
    {"state_pair": ["<id_a>", "<id_b>"], "risk": "<чому ці два стани важко відрізнити>"}
  ],
  "confidence_self_assessment": {
    "overall_confidence_pct": <0-100>,
    "weakest_state_id": "<id>",
    "weakest_state_reason": "<чому>"
  },
  "self_check": {
    "states_count_in_range_8_to_12": <true|false>,
    "traffic_share_sums_to_100": <true|false>,
    "all_post_response_actions_sum_to_100": <true|false>,
    "all_transition_matrix_rows_sum_to_100": <true|false>,
    "all_transitions_reference_existing_ids": <true|false>,
    "at_least_one_non_trading_state": <true|false>,
    "typical_questions_count_5_to_8_for_each": <true|false>,
    "any_field_skipped_or_templated": <true|false>
  }
}
```

## Повний приклад однієї персони (структура, не копіювати в свою відповідь)

```
{
  "id": "panic_position_holder",
  "one_liner": "Має відкриту позицію в просадці, шукає що робити прямо зараз",
  "expected_traffic_share_pct": 12,
  "typical_server_context": {
    "balance_usdt_range": [500, 5000],
    "has_open_positions": "true",
    "positions_pnl_state": "loss",
    "risk_preference": ["medium", "risky"],
    "has_active_strategies": "sometimes",
    "active_strategies_count_range": [0, 1]
  },
  "emotional_tone": "anxiety",
  "behavioral_patterns": {
    "typing_style": "fragments",
    "typo_frequency": "frequent",
    "language_mix": "mixed_ru_en",
    "profanity": "rare",
    "avg_messages_per_session": 6,
    "avg_session_duration_minutes": 4,
    "repeat_rate_pct": 60
  },
  "typical_questions": [
    "блін шо з солою",
    "выходить или ждать",
    "сольет?",
    "поможи срочно SOL -8%",
    "что делать если в минусе уже",
    "стопить или докупать",
    "норм цена для входа?"
  ],
  "post_response_actions": [
    {"action": "ask_followup", "probability_pct": 50},
    {"action": "click_card", "probability_pct": 20},
    {"action": "ignore", "probability_pct": 20},
    {"action": "leave_chat", "probability_pct": 10}
  ],
  "state_transitions": [
    {"to": "panic_position_holder", "trigger": "відповідь не заспокоїла", "probability_pct": 40},
    {"to": "frustrated_complainer", "trigger": "позиція пішла ще нижче", "probability_pct": 30},
    {"to": "cautious_planner", "trigger": "взяв себе в руки, хоче план", "probability_pct": 30}
  ]
}
```

## Правила якості (обов'язково перечитати перед заповненням)

1. **8-12 станів. Сума traffic_share_pct = 100.** Сума probability_pct у кожному `post_response_actions` = 100. Сума по кожному рядку `transition_matrix` = 100 (включно з self-loop).

2. **1-2 стани мають бути не-торгові.** Флуд, скарга, тестування "що ти вмієш", ботоподібна активність. Реальні чати завжди мають такий трафік.

3. **Розподіл трафіку не рівномірний.** Якщо ти даєш кожному стану 8-12% — це халтура. Реальність скошена: один-два домінуючих стани (20-35%), решта в довгому хвості.

4. **Реалістична мова в typical_questions.** Користувачі WhiteBIT (українсько-східноєвропейське ядро, міжнародна аудиторія) пишуть коротко, з помилками, на суміші мов, матюкаються, шлють фрагменти ("шо там", "сольет?", "хелп"). Як мінімум половина запитів — такі. Якщо для одного стану всі питання граматично правильні англійські — це підозріло.

5. **Кожна персона унікальна по поведінці.** Якщо ловиш себе на тому що behavioral_patterns для двох станів однакові — зупинись і подумай чим вони реально різняться.

6. **state_transitions має 2-4 переходи** з різних станів. Один з переходів може бути self-loop (залишився в тому ж стані). Сума probability_pct у state_transitions може бути <100 (це не повна матриця, це список найважливіших переходів). А ось `transition_matrix` — повна, сума по рядку = 100.

7. **transition_matrix будується після того як описано всі states.** Це окреме поле в JSON, не дублювати з state_transitions. У transition_matrix перелічи ВСІ N×N клітинок (для відсутніх переходів став 0).

8. **Не використовуй ML-жаргон.** Заборонено: POMDP, HMM, belief state, policy, reward, classifier. Ти продуктовий аналітик, не ML-інженер.

9. **Заповни self_check добросовісно.** Якщо щось не вдалося — постав `false` і виправ перш ніж видати JSON. `any_field_skipped_or_templated: false` має бути true після перевірки.

10. **Жодного тексту поза JSON-блоками.** Не пиши "ось мій JSON:", не обгортай у markdown ` ``` `. Кожна частина — від `{` до `}`. Якщо частин декілька — між ними може бути порожній рядок або одне коротке слово-роздільник ("---" або "PART 2"), решта тексту заборонена.

11. **Можна розбити відповідь на 2-3 частини** якщо боїшся не вмістити все в один блок. Правила розбиття — в таблиці вище. Кожна частина — окремий валідний JSON з власним meta. `submission_id` однаковий для всіх частин. `part_number` і `total_parts` добросовісні. Якщо вирішив розбити — вкажи `total_parts` у Part 1 коректно, не міняй потім.

---

Тепер пиши JSON. Без вступу. Один або кілька JSON-блоків відповідно до правил розбиття.
