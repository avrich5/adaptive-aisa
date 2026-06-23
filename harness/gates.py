"""
Validation gates. Every point row must pass before writing to data/.
Rules from CLAUDE.md Gates section.
"""
from harness.action_space import ALL_ACTIONS

OBSERVABLE_COLS = frozenset([
    'persona_id', 'run_id', 'checkpoint_idx', 'window_id',
    'drawdown', 'regime', 'time_in_position', 'recent_action_history',
    'action',
])
HIDDEN_COLS = frozenset([
    'anxiety', 'trust', 'market_understanding', 'regime_awareness', 'exit_propensity',
])


class GateError(ValueError):
    pass


def validate_row(row: dict) -> None:
    """Raise GateError if the row fails any gate. Call before appending to dataset."""

    if not row.get('regime'):
        raise GateError(f"Gate 1: missing regime in run={row.get('run_id')} idx={row.get('checkpoint_idx')}")

    if row['regime'] == 'UNCLASSIFIED':
        raise GateError(
            f"Gate 2: UNCLASSIFIED regime run={row.get('run_id')} idx={row.get('checkpoint_idx')}. "
            "Policy: reject. To include, update gates.py and document."
        )

    for field in ('drawdown', 'time_in_position'):
        if row.get(field) is None:
            raise GateError(f"Gate 3: empty context field {field!r} in run={row.get('run_id')}")

    if HIDDEN_COLS & OBSERVABLE_COLS:
        raise GateError(f"Gate 4: hidden vector leaks into observable cols: {HIDDEN_COLS & OBSERVABLE_COLS}")

    if row.get('action') not in ALL_ACTIONS:
        raise GateError(f"Gate 5: unknown action {row.get('action')!r}")

    required = OBSERVABLE_COLS | HIDDEN_COLS
    missing = required - set(row.keys())
    if missing:
        raise GateError(f"Gate 6: missing fields {missing}")
