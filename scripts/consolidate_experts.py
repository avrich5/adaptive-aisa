#!/usr/bin/env python3
"""
consolidate_experts.py — детерминированная консолидация ответов экспертов
по User States для WhiteBIT AI Strategy Advisor.

Что делает (БЕЗ LLM, чистый Python):
  1. Загружает все *.json из experts/ (и experts/invalid/ помечает отдельно).
  2. Группирует части по meta.submission_id, проверяет полноту (part_number/total_parts).
  3. Мерджит части одного эксперта в единый объект.
  4. Валидирует по правилам схемы H (суммы вероятностей, ссылки transition_matrix,
     наличие required-полей, диапазон states 8-12).
  5. Считает per-expert и cross-expert статистику.
  6. Пишет:
       personas/_merged/<expert_id>.json        — склеенный объект на эксперта
       personas/_report/validation_report.md    — человекочитаемый отчёт
       personas/_report/all_states_flat.json     — плоский список ВСЕХ состояний
                                                    всех экспертов (вход для LLM-консенсуса)

Семантический консенсус (маппинг разных id одного состояния, напр.
panic_position_holder == panic_holder == loss_panicker) этот скрипт НЕ делает —
он готовит чистый вход для LLM-шага. См. ТЗ в конце.

Usage:
    python3 scripts/consolidate_experts.py
    python3 scripts/consolidate_experts.py --root /Users/andriy/wbprd_macbook/adaptive_aisa
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# --- поля payload по content_type (из H) ---
METADATA_FIELDS = [
    "edge_cases_not_covered",
    "questions_for_whitebit_team",
    "classification_risks",
    "confidence_self_assessment",
    "self_check",
]
CONTENT_TYPE_FIELDS = {
    "full": ["states", "transition_matrix"] + METADATA_FIELDS,
    "states": ["states"],
    "matrix": ["transition_matrix"],
    "metadata": METADATA_FIELDS,
    "states_and_matrix": ["states", "transition_matrix"],
}

TOL = 1  # допуск на округление при проверке сумм процентов (в п.п.)


# ---------------------------------------------------------------------------
# Loading & grouping
# ---------------------------------------------------------------------------

def load_raw_files(experts_dir: Path):
    """Возвращает (valid_docs, broken). valid_docs: list[(path, dict)]."""
    valid, broken = [], []
    for path in sorted(experts_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            valid.append((path, doc))
        except Exception as e:
            broken.append((path, f"JSON parse error: {e}"))
    # invalid/ — заведомо проблемные, фиксируем но не мерджим
    invalid_dir = experts_dir / "invalid"
    if invalid_dir.is_dir():
        for path in sorted(invalid_dir.glob("*.json")):
            broken.append((path, "located in invalid/ — excluded from consensus"))
    return valid, broken


def group_by_submission(valid_docs):
    """submission_id -> list[(path, doc)] отсортировано по part_number."""
    groups = defaultdict(list)
    orphans = []  # документы без meta.submission_id
    for path, doc in valid_docs:
        meta = doc.get("meta", {})
        sid = meta.get("submission_id")
        if not sid:
            orphans.append((path, doc))
            continue
        groups[sid].append((path, doc))
    for sid in groups:
        groups[sid].sort(key=lambda pd: pd[1].get("meta", {}).get("part_number", 0))
    return groups, orphans


# ---------------------------------------------------------------------------
# Merge parts of one submission
# ---------------------------------------------------------------------------

def merge_submission(parts):
    """parts: list[(path, doc)] одного submission_id. Возвращает (merged, issues)."""
    issues = []
    metas = [doc.get("meta", {}) for _, doc in parts]
    expert_ids = {m.get("expert_id") for m in metas}
    if len(expert_ids) > 1:
        issues.append(f"conflicting expert_id across parts: {expert_ids}")
    expert_id = metas[0].get("expert_id", "UNKNOWN")

    total_parts = metas[0].get("total_parts", 1)
    declared = {m.get("part_number") for m in metas}
    expected = set(range(1, total_parts + 1))
    if declared != expected:
        issues.append(
            f"incomplete/duplicate parts: declared total_parts={total_parts}, "
            f"got part_numbers={sorted(p for p in declared if p is not None)}"
        )

    merged = {"meta": {"expert_id": expert_id,
                       "submission_id": metas[0].get("submission_id"),
                       "merged_from_parts": len(parts)}}
    for path, doc in parts:
        ctype = doc.get("meta", {}).get("content_type", "full")
        for field in CONTENT_TYPE_FIELDS.get(ctype, []):
            if field in doc:
                if field in merged:
                    issues.append(f"duplicate field '{field}' across parts")
                merged[field] = doc[field]
        # подхватываем и любые лишние поля, не описанные content_type
        for k, v in doc.items():
            if k != "meta" and k not in merged:
                merged[k] = v
    return merged, issues


# ---------------------------------------------------------------------------
# Validation (rules from H_expert_prompt_user_states.md)
# ---------------------------------------------------------------------------

def _sum_pct(items, key):
    return sum(float(i.get(key, 0) or 0) for i in items)


def validate_merged(merged):
    """Возвращает list[str] предупреждений/ошибок. Пусто => всё чисто."""
    errs = []
    eid = merged.get("meta", {}).get("expert_id", "?")
    states = merged.get("states")
    if not states:
        errs.append("NO states present")
        return errs

    # 1. количество состояний 8-12
    if not (8 <= len(states) <= 12):
        errs.append(f"states_count={len(states)} OUT OF RANGE 8..12")

    state_ids = [s.get("id") for s in states]
    dupes = {x for x in state_ids if state_ids.count(x) > 1}
    if dupes:
        errs.append(f"duplicate state ids: {dupes}")

    # 2. сумма traffic_share = 100
    tshare = _sum_pct(states, "expected_traffic_share_pct")
    if abs(tshare - 100) > TOL:
        errs.append(f"traffic_share sum = {tshare} (!=100)")

    # 3. >=1 неторгового состояния (эвристика по id/one_liner)
    nontrade_markers = ("test", "troll", "bot", "churn", "leav", "complain",
                        "frustr", "angry", "ui", "ops", "observer", "inactive",
                        "passive", "watch", "monitor")
    if not any(any(m in (s.get("id", "") + s.get("one_liner", "")).lower()
                   for m in nontrade_markers) for s in states):
        errs.append("no obvious non-trading state (heuristic) — verify manually")

    # 4. post_response_actions суммируются к 100; typical_questions 5-8
    for s in states:
        sid = s.get("id", "?")
        pra = s.get("post_response_actions", [])
        psum = _sum_pct(pra, "probability_pct")
        if pra and abs(psum - 100) > TOL:
            errs.append(f"[{sid}] post_response_actions sum = {psum} (!=100)")
        tq = s.get("typical_questions", [])
        if not (5 <= len(tq) <= 8):
            errs.append(f"[{sid}] typical_questions count = {len(tq)} (want 5..8)")

    # 5. transition_matrix: квадрат, строки=100, ссылки на существующие id
    tm = merged.get("transition_matrix")
    if not tm:
        errs.append("NO transition_matrix")
    else:
        sid_set = set(state_ids)
        missing_rows = sid_set - set(tm.keys())
        extra_rows = set(tm.keys()) - sid_set
        if missing_rows:
            errs.append(f"transition_matrix missing rows: {missing_rows}")
        if extra_rows:
            errs.append(f"transition_matrix has unknown rows: {extra_rows}")
        for row_id, row in tm.items():
            bad_cols = set(row.keys()) - sid_set
            if bad_cols:
                errs.append(f"matrix row '{row_id}' references unknown ids: {bad_cols}")
            rsum = _sum_pct([row], None) if False else sum(float(v or 0) for v in row.values())
            if abs(rsum - 100) > TOL:
                errs.append(f"matrix row '{row_id}' sum = {rsum} (!=100)")

    # 6. self_check честность
    sc = merged.get("self_check", {})
    if isinstance(sc, dict):
        if sc.get("any_field_skipped_or_templated") is True:
            errs.append("self_check admits skipped/templated fields")
        for flag in ("traffic_share_sums_to_100", "all_post_response_actions_sum_to_100",
                     "all_transition_matrix_rows_sum_to_100",
                     "all_transitions_reference_existing_ids"):
            if sc.get(flag) is False:
                errs.append(f"self_check flag {flag}=false (self-reported)")
    return errs


# ---------------------------------------------------------------------------
# Reporting & outputs
# ---------------------------------------------------------------------------

def build_flat_states(merged_by_expert):
    """Плоский список всех состояний всех экспертов — вход для LLM-консенсуса."""
    flat = []
    for eid, merged in merged_by_expert.items():
        for s in merged.get("states", []):
            flat.append({
                "expert_id": eid,
                "submission_id": merged.get("meta", {}).get("submission_id"),
                "id": s.get("id"),
                "one_liner": s.get("one_liner"),
                "expected_traffic_share_pct": s.get("expected_traffic_share_pct"),
                "emotional_tone": s.get("emotional_tone"),
                "typical_server_context": s.get("typical_server_context"),
                "typical_questions": s.get("typical_questions", [])[:3],
            })
    return flat


def write_outputs(root: Path, merged_by_expert, flat, report_lines):
    merged_dir = root / "personas" / "_merged"
    report_dir = root / "personas" / "_report"
    merged_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    for eid, merged in merged_by_expert.items():
        safe = eid.replace("/", "_").replace(" ", "_")
        (merged_dir / f"{safe}.json").write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    (report_dir / "all_states_flat.json").write_text(
        json.dumps(flat, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "validation_report.md").write_text(
        "\n".join(report_lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/Users/andriy/wbprd_macbook/adaptive_aisa")
    args = ap.parse_args()
    root = Path(args.root)
    experts_dir = root / "experts"

    valid_docs, broken = load_raw_files(experts_dir)
    groups, orphans = group_by_submission(valid_docs)

    R = ["# Expert Consolidation — Validation Report", ""]
    R.append(f"- Source: `{experts_dir}`")
    R.append(f"- Valid JSON files: {len(valid_docs)}")
    R.append(f"- Submissions (by submission_id): {len(groups)}")
    R.append(f"- Broken / excluded: {len(broken)}")
    R.append("")

    merged_by_expert = {}
    total_states = 0
    for sid, parts in groups.items():
        merged, merge_issues = merge_submission(parts)
        eid = merged["meta"]["expert_id"]
        errs = validate_merged(merged)
        merged_by_expert[eid] = merged
        n_states = len(merged.get("states", []))
        total_states += n_states
        R.append(f"## {eid}  (`{sid}`)")
        R.append(f"- parts merged: {merged['meta']['merged_from_parts']}")
        R.append(f"- states: {n_states} -> {[s.get('id') for s in merged.get('states', [])]}")
        conf = merged.get("confidence_self_assessment", {})
        if conf:
            R.append(f"- self-confidence: {conf.get('overall_confidence_pct')}%  "
                     f"(weakest: {conf.get('weakest_state_id')})")
        all_issues = merge_issues + errs
        if all_issues:
            R.append(f"- ⚠️ ISSUES ({len(all_issues)}):")
            R.extend(f"    - {x}" for x in all_issues)
        else:
            R.append("- ✅ no validation issues")
        R.append("")

    if orphans:
        R.append("## Orphans (no submission_id)")
        R.extend(f"- {p}" for p, _ in orphans)
        R.append("")
    if broken:
        R.append("## Broken / excluded")
        R.extend(f"- `{p.name}`: {why}" for p, why in broken)
        R.append("")

    R.append("## Cross-expert summary")
    R.append(f"- experts merged: {len(merged_by_expert)}")
    R.append(f"- total states across all experts: {total_states}")
    R.append("")
    R.append("## Next step (NOT done by this script): semantic consensus")
    R.append("See `personas/_report/all_states_flat.json` — feed it to an LLM to cluster")
    R.append("equivalent states across experts (e.g. panic_position_holder ≈ panic_holder")
    R.append("≈ loss_panicker) and produce the consensus 8-12 User States taxonomy.")

    flat = build_flat_states(merged_by_expert)
    write_outputs(root, merged_by_expert, flat, R)

    print("\n".join(R))
    print(f"\nWrote: personas/_merged/*.json, personas/_report/validation_report.md, "
          f"personas/_report/all_states_flat.json")


if __name__ == "__main__":
    main()
