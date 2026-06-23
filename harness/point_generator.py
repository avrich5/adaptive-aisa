"""
Core generation loop: persona x drawdown_window -> list of flat point rows.
Atom = row. Trajectory = group by run_id. Trajectory not stored separately.
"""
import hashlib
import yaml
from pathlib import Path
from typing import Optional

from harness.action_space import TERMINAL_ACTIONS
from harness.market_loader import MarketLoader, get_weekly_dates
from harness.persona_model import Persona, HiddenVector, load_personas
from harness.gates import validate_row, GateError

WINDOWS_CONFIG = Path(__file__).parent.parent / 'config' / 'windows.yaml'


def _run_id(persona_id: str, window_id: str) -> str:
    h = hashlib.sha1(f"{persona_id}|{window_id}".encode()).hexdigest()[:8]
    return f"{persona_id}__{window_id}__{h}"


def _format_recent(actions: list, n: int = 3) -> str:
    return ';'.join(actions[-n:]) if actions else ''


def generate_run(
    persona: Persona,
    window: dict,
    loader: MarketLoader,
    max_checkpoints: Optional[int] = None,
) -> list:
    run_id = _run_id(persona.id, window['id'])
    dates = get_weekly_dates(window['start_date'], window['end_date'])
    if max_checkpoints:
        dates = dates[:max_checkpoints]

    rows = []
    recent_actions = []
    vec: HiddenVector = persona.fresh_vector()
    terminated = False

    for idx, date in enumerate(dates):
        if terminated:
            break

        ctx = loader.get_context(window['asset'], date)
        if ctx is None:
            continue

        # UNCLASSIFIED: explicit policy — skip row, continue run
        # (Gate 2 would reject it, so we skip before building the row)
        if not ctx.is_valid:
            continue

        result = persona.decide(vec, ctx, idx, recent_actions)
        vec = result.vector

        row = {
            # Labels
            'persona_id': persona.id,
            'run_id': run_id,
            'checkpoint_idx': idx,
            'window_id': window['id'],
            # Observable context (clustering input)
            'drawdown': round(ctx.drawdown, 4),
            'regime': ctx.regime,
            'time_in_position': idx * 7,
            'recent_action_history': _format_recent(recent_actions),
            # Hidden vector (answer key, NOT for clustering)
            'anxiety': round(result.vector.anxiety, 4),
            'trust': round(result.vector.trust, 4),
            'market_understanding': round(result.vector.market_understanding, 4),
            'regime_awareness': round(result.vector.regime_awareness, 4),
            'exit_propensity': round(result.vector.exit_propensity, 4),
            # Target
            'action': result.action,
            # Debug fields (strip before clustering)
            '_reasoning': result.reasoning_template,
            '_date': date,
            '_close': round(ctx.close_price, 2),
        }

        try:
            validate_row(row)
        except GateError as e:
            print(f"  [gate skip] {e}")
            continue

        rows.append(row)
        recent_actions.append(result.action)

        if result.action in TERMINAL_ACTIONS:
            terminated = True

    return rows


def generate_dataset(
    exchange: str = 'whitebit',
    persona_ids: Optional[list] = None,
    window_ids: Optional[list] = None,
    seed: int = 42,
    max_checkpoints: Optional[int] = None,
) -> list:
    """Generate all rows for selected personas x windows."""
    import random
    rng = random.Random(seed)

    loader = MarketLoader(exchange)
    loader.load()
    print(f"Loaded regime data: exchange={exchange}")

    all_personas = load_personas(rng)
    personas = [p for p in all_personas if not persona_ids or p.id in persona_ids]

    with open(WINDOWS_CONFIG) as f:
        wcfg = yaml.safe_load(f)
    windows = [w for w in wcfg['windows'] if not window_ids or w['id'] in window_ids]

    print(f"Running {len(personas)} personas x {len(windows)} windows")

    all_rows = []
    for persona in personas:
        for window in windows:
            rows = generate_run(persona, window, loader, max_checkpoints=max_checkpoints)
            print(f"  {persona.id} x {window['id']}: {len(rows)} points")
            all_rows.extend(rows)

    print(f"Total rows generated: {len(all_rows)}")
    return all_rows
