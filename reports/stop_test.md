# TASK 04.5 — STOP_TEST v3 (фінальний)

**Дата:** 2026-06-23.
**Джерело:** `llm_training_dev.strategy_benchmark` ⋈ `ai_orchestrator.dev.strategies` по brute_id
**N=4,056** (BTC=1,483 · SOL=1,335 · ETH=1,238)

> v1 (N=28, skufs_profit_radar) і v2 (roi_avg-sort) анульовано. Причини — нижче.

---

## Шаг 0 — зафіксовано ДО розрахунку

### Поле сортування оркестратора (rag_searcher.py, рядок ~450)

```python
candidates.sort(key=lambda x: x.best_fitness * (1 + max(x.best_roi, 0) / 100), reverse=True)
```

- `best_fitness` = regex з `data->'factual_description'->'actionable_guidance'[1]`: pattern `(\d+\.?\d*) fitness`
- `best_roi` = `benchmark.roi_avg` (WB benchmark `strategy_benchmark.roi_avg`) коли benchmark є

**Перевірка monotonicity roi_avg → composite key (Spearman, ai_orchestrator.dev.strategies):**

| Asset | corr(best_fitness, roi_avg) | corr(roi_avg, composite_key) | N |
|---|---|---|---|
| BTC | 0.170 | 0.518 | 6,141 |
| SOL | 0.190 | 0.628 | 5,603 |
| ETH | 0.135 | 0.498 | 5,913 |

**Висновок:** `corr(best_fitness, roi_avg) = 0.14–0.19` — далеко від порогу 0.8. Composite ≠ roi_avg sort. v2 (sort by roi_avg) анульовано, потрібен перегін з правильним ключем.

### Per-regime джерело

`strategy_benchmark.per_regime_display.roi_pct`, ключі: `range`, `stress`, `trending_up`, `trending_down`.

### Маппінг 12→4 (`regime_tagger.py::REGIME_MACRO_GROUPS`)

```python
"trending_up":   {"R1_BULL_TREND", "R6_ACCUMULATION"}
"trending_down": {"R2_BEAR_TREND", "R7_DISTRIBUTION", "R8_CAPITULATION"}
"range":         {"R3_RANGE", "R5_LOW_VOLATILITY", "R9_SPECULATIVE_MANIA"}
"stress":        {"R4_HIGH_VOLATILITY", "R10_LIQUIDITY_STRESS", "R11_STRUCTURAL_TRANSITION", "R12_REGIME_TRANSITION"}
```

### Ваги режимів (aggregate signals з 4,056 benchmark рядків)

| Режим | Signals | Вага |
|---|---|---|
| range | 214,682 | 36.6% |
| trending_up | 226,026 | 38.5% |
| stress | 79,308 | 13.5% |
| trending_down | 67,303 | 11.5% |

*(base-states `/api/history` має тільки 37 снапшотів за 2.5 місяці — замало. Ваги з WB backtest сигналів.)*

### Поріг змістовності (фіксований до розрахунку)

`|rho| ≥ 0.3`. Глибина топа: 3.

---

## Покриття

| Asset | N в strategy_benchmark | N з fitness | % |
|---|---|---|---|
| BTC | 1,483 | 1,483 | 100% |
| SOL | 1,335 | 1,335 | 100% |
| ETH | 1,238 | 1,238 | 100% |
| **TOTAL** | **4,056** | **4,056** | **100%** |

`best_fitness` покриття: 2,469 uniq (brute_id, asset) з ai_orchestrator → повний перетин з benchmark.

---

## Spearman rho: composite sort key ↔ per-regime rank

Sort key: `best_fitness × (1 + max(roi_avg, 0) / 100)`, descending.

### Per-cell

| Клітина | N | rho | |
|---|---|---|---|
| BTC × range | 1,483 | +0.329 | **CONTENT** |
| BTC × stress | 1,483 | +0.251 | noise |
| BTC × trending_up | 1,483 | +0.117 | noise |
| BTC × trending_down | 1,483 | −0.176 | noise |
| SOL × range | 1,335 | +0.323 | **CONTENT** |
| SOL × stress | 1,335 | +0.412 | **CONTENT** |
| SOL × trending_up | 1,335 | +0.338 | **CONTENT** |
| SOL × trending_down | 1,335 | +0.350 | **CONTENT** |
| ETH × range | 1,238 | +0.372 | **CONTENT** |
| ETH × stress | 1,238 | +0.221 | noise |
| ETH × trending_up | 1,238 | +0.232 | noise |
| ETH × trending_down | 1,238 | +0.223 | noise |

### Гістограма

```
[-1.01,−0.75)                                  0
[−0.75,−0.50)                                  0
[−0.50,−0.25)                                  0
[−0.25,+0.00) █                                1
[+0.00,+0.25) ████                             4
[+0.25,+0.50) ███████                          7
[+0.50,+0.75)                                  0
[+0.75,+1.01)                                  0
```

### Зведені метрики

| Метрика | Значення |
|---|---|
| Незважена медіана rho | **+0.287** |
| Зважена медіана rho | **+0.323** |
| Частка rho < 0 | 1/12 = 8.3% (незважена) · 3.8% (зважена) |
| Content клітини (|rho|≥0.3) | **6/12 (50%)** — всі positive |

### Per-regime зведення

| Режим | Median rho | BTC | SOL | ETH | |
|---|---|---|---|---|---|
| range | +0.329 | +0.329 | +0.323 | +0.372 | **CONTENT** всі 3 |
| stress | +0.251 | +0.251 | +0.412 | +0.221 | noise (SOL CONTENT) |
| trending_up | +0.232 | +0.117 | +0.338 | +0.232 | noise (SOL CONTENT) |
| trending_down | +0.223 | −0.176 | +0.350 | +0.223 | noise (SOL CONTENT) |

---

## Топ-3 інверсія

100% в усіх 12 клітинах (медіана=1.00, mean=1.00).

**Пояснення:** Spearman rho=0.3+ і топ-3 інверсія=100% не суперечать одне одному. При N≈1,300+ Spearman вимірює глобальну кореляцію рангів. Топ-3 конкретні переможці в такому пулі майже ніколи не збігаються через щільну конкуренцію у верхньому сегменті. **Висновок:** composite sort дає статистично кращий-ніж-випадковий per-regime результат на рівні всієї популяції, але не ідентифікує per-regime чемпіона серед топ-3 імен.

---

## ВЕРДИКТ

### Правило рішення (зафіксовано до прогону)
- Branch 1: weighted median rho ≥ 0.3 → H1 виживає → TASK 05
- Branch 2: 0 < weighted median < 0.3 → per-regime рекомендатор
- Branch 3: weighted median ~0 або від'ємна → СТОП

### Числа

| Метрика | Значення | vs поріг |
|---|---|---|
| Зважена медіана rho | **+0.323** | ≥ 0.3 ✓ |
| Незважена медіана rho | **+0.287** | < 0.3 (нижче) |
| Частка rho < 0 | 8.3% | — |
| Content клітини | 6/12 (50%) | більшість positive |

### **BRANCH 1 — H1 виживає. TASK 05 починається.**

Зважена медіана rho = +0.323 ≥ 0.3. Переважають додатні значення, нуль або близькі до нуля від'ємні.

**Обґрунтування:**
1. Зважена медіана на межі порогу, але перевищує його. Незважена = 0.287 — нижче, тому вердикт умовний.
2. **SOL (N=1,335)** — єдиний актив з усіма 4 режимами CONTENT (0.32–0.41). Стійкий сигнал.
3. **range** — єдиний режим, де всі 3 активи CONTENT (BTC/SOL/ETH: 0.33/0.32/0.37).
4. **BTC trending_down** — єдина від'ємна клітина (rho=−0.18), але нижче порогу (noise).
5. Топ-3 інверсія 100% = рекомендація правильна статистично, але не гарантує top-3 по імені.

---

## Застереження для TASK 05

1. **Зважена медіана на межі (0.323 ≈ поріг 0.3).** Якщо в TASK 05 виникне систематичне розходження trust у BTC trending_down або ETH stress — це підтвердить слабкість цих клітин і треба перейти на per-regime рекомендацію.

2. **BTC trending_down — ненадійна зона** (rho=−0.18). Composite sort може рекомендувати стратегії, що гірше за середнє в trending_down для BTC.

3. **Composite vs roi_avg sort:**
   - `corr(roi_avg, composite_key)` = 0.50–0.63. Це дає КРАЩИЙ per-regime результат при sort by roi_avg (v2 weighted median = 0.416) ніж при composite sort (v3 = 0.323).
   - Причина: `best_fitness` і `roi_avg` слабко корельовані (0.14–0.19). Composite ключ додає шум відносно roi_avg.
   - Практичний наслідок: оркестратор, оптимізований під `best_fitness`, обирає стратегії, що не є оптимальними за per-regime roi_pct.

4. **Топ-3 інверсія 100%.** Оркестратор дає вибірку краще за випадкову (rho > 0), але конкретні TOP-3 strat by composite_key майже ніколи не є per-regime чемпіонами.

---

## Версії та анулювання

| Версія | N | Sort key | Weighted median rho | Причина анулювання |
|---|---|---|---|---|
| v1 | 28 | roi_avg | +0.213 | читав локальне дзеркало (skufs), не production factory DB |
| v2 | 4,056 | roi_avg | +0.416 | corr(best_fitness, roi_avg)=0.14–0.19 → sort key ≠ prod sort |
| **v3 (фінал)** | **4,056** | **composite** | **+0.323** | **— фінальний** |

---

*v3 прогнано 2026-06-23. Не перевідкривати без нових даних або зміни sort key в rag_searcher.py.*
