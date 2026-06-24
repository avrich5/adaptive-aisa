# GROUNDTRUTH — зафіксована істина (per_regime_display + крива)

Перевірено по коду 2026-06-24. Джерело: wbprd_skufs mirror (git актуальний).

---

## 1. Де і як обчислюється per_regime_display

**Файл:** `llm-training-data-miner/src/.../factory/benchmark/regime_tagger.py`
**Функція:** `compute_regime_breakdowns(tagged_trades, capital_usd)`

**Формула:**
```
roi_pct = sum(trade.Returns for trade in regime_bucket) / capital * 100
```

- `capital` = `max_pos_actual` з `compute_all_metrics()` (metrics.py) — пік відкритої позиції за весь прогін
- `trade.Returns` = поле з `trading-report.csv` (реалізований PnL за угоду, до комісії)
- Маппінг 12 → 4 макро-бакети:
  - `trending_up`   = {R1_BULL_TREND, R6_ACCUMULATION}
  - `trending_down` = {R2_BEAR_TREND, R7_DISTRIBUTION, R8_CAPITULATION}
  - `range`         = {R3_RANGE, R5_LOW_VOLATILITY, R9_SPECULATIVE_MANIA}
  - `stress`        = {R4_HIGH_VOLATILITY, R10_LIQUIDITY_STRESS, R11_STRUCTURAL_TRANSITION, R12_REGIME_TRANSITION}
- Режим кожної угоди: `base-states /api/history` за датою відкриття (UTC)

**Зберігається:** `dev.strategy_benchmark.per_regime_display` (JSONB, profit_radar DB)
**Ключі JSONB:** `{range, stress, trending_up, trending_down}` → `{roi_pct, signals, win_rate}`

---

## 2. Період (вікно бектесту)

**Файл:** `factory/benchmark/backtest_runner.py`
**Константа:** `BENCHMARK_LOOKBACK_YEARS=3` (env, default=3)

```
end_dt   = UTC midnight of experiment_created_at date
start_dt = end_dt - 365 * BENCHMARK_LOOKBACK_YEARS days
```

Anchor: дата, коли стратегія була записана в експеримент (не поточна дата).
Різні стратегії з різних експериментів → різні абсолютні вікна, але ОДНАКОВА тривалість (3Y).

---

## 3. Fitness: дві різні метрики — НЕ одна

| Метрика | Що це | Формула | Де живе |
|---|---|---|---|
| `per_regime_display.roi_pct` | cumulative trade PnL / capital | простий % | `strategy_benchmark` |
| `roi_avg` (benchmark) | те саме що roi_pct але за весь прогін | простий % | `strategy_benchmark.roi_avg` |
| `best_fitness` (ATSA) | fitnessTanh з brute-force | tanh-комбінація ROI + risk | парситься з `factual_description` тексту |

**fitnessTanh (scalping-pnl/connectors/math_functions.js:1397):**
```js
roi  = total_row.roi / 100
risk = max(2 * MDD_pct / 100, abs(min_pnl / max_grid_amount))
reward_factor = 0.5 * (1 + tanh(sensitivity * (roi - reward_threshold)))
risk_factor   = 0.5 * (1 - tanh(sensitivity * (risk - penalty_threshold)))
fitness       = reward_factor * risk_factor * (1 + penalty)  // penalty=-1 if roi<0
```

**Параметри в prod-конфігах (різняться між прогонами):**
- `darvin/config/config.json`:   `{penalty: 0.1, reward: 0.25, sensitivity: 5}`
- `darvin/config/template_f.json`: `{penalty: 0.15, reward: 0.25, sensitivity: 4}`
- `config_examples/brute_generate_munations.json`: `{penalty: 0.1, reward: 0.25, sensitivity: 5}`

**Висновок:** `best_fitness` значення з різних brute-force прогонів з різними параметрами — НЕ порівнянні між собою. `roi_avg` і `per_regime_display.roi_pct` — порівнянні (однакова формула, нормалізовані у %).

**Підтверджено:** corr(`best_fitness`, `roi_avg`) = 0.14–0.19 (майже ортогональні).
ATSA сортує по `best_fitness * (1 + max(best_roi,0)/100)` — фактично по fitness, не по ROI.

---

## 4. Сумісність N=4056 рядків

`per_regime_display.roi_pct` і `roi_avg` — СУМІСНІ між усіма рядками:
- Одна формула (regime_tagger.py)
- Нормалізовані у % (capital = власний max_pos_actual кожної стратегії)
- Різні абсолютні вікна не порушують сумісність — у % порівнювати можна

`best_fitness` — НЕСУМІСНИЙ між прогонами з різними `fitness_function` параметрами.
Висновок для STOP_TEST v3: `roi_avg` як предиктор рангу — коректно, `best_fitness` — ні.

---

## 5. Крива: чи та сама іде в харнес

**ЩО є groundtruth:** продовження equity-кривої стратегії після T (фактичний ROI через k чекпоінтів).
**ДЕ лежить:** `scalping-pnl/results/{run_id}/qpnls.csv` (поле `balance`); доступно через `GET /backtest-run/{id}/equity` (factory-api :8006).
Зв'язок: `brute_{brute_id}_{settings_id}_{ASSET}USDT` → `dev.backtest_runs` (is_benchmark=TRUE) → `backtest_instance_url` → scalping-pnl endpoint.

**ЯК звіряється:** персона перебуває на ділянці [T-w, T] кривої; вихід виправданий якщо крива після T продовжує падати; утримання виправдане якщо крива відновлюється.

**КРИТИЧНО — стан ЗАРАЗ:**
Поточний харнес (TASK 02) = drawdown-вікна на OHLCV ціні активу.
Benchmark-крива (qpnls) = equity стратегії на базі trade PnL.
**Це РІЗНІ криві. Groundtruth-звірка зараз хибна.**

До виконання TASK 05 (доробка харнесу під qpnls):
- harness крива ≠ benchmark крива
- довіряти gate TASK 04 неможливо

---

## 6. Процедура перевірки (після TASK 05)

1. Отримати `qpnls.csv` для стратегії X через factory-api або кеш
2. Визначити T = точка рекомендації оркестратора
3. Персона "проживає" ділянку [T-w, T] → приймає дію
4. Groundtruth = factual `balance` на T+k (k = наступні чекпоінти у qpnls)
5. Вихід на T ВИПРАВДАНИЙ якщо `balance[T+k] < balance[T]` (крива далі впала)
6. Утримання ВИПРАВДАНЕ якщо `balance[T+k] > balance[T]` (крива відновилась)

Обидві сторони (3 і 4) повинні читати ОДИН і той самий `qpnls.csv` одного `run_id`.

---

*Зафіксовано: 2026-06-24. Наступне оновлення — після TASK 05 (доробка харнесу під qpnls).*
