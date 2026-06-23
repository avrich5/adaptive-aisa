"""
7 persona implementations. Parameters from config/personas.yaml.
Status: DRAFT — calibrate after consensus_user_states.json is produced.
Decision logic: deterministic-probabilistic (no LLM in core loop).
"""
import copy
import random
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from harness.action_space import CHAT_ACTIONS, TERMINAL_ACTIONS, SILENCE
from harness.market_loader import MarketContext

CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'personas.yaml'


@dataclass
class HiddenVector:
    anxiety: float
    trust: float
    market_understanding: float
    regime_awareness: float
    exit_propensity: float


@dataclass
class DecisionResult:
    action: str
    vector: HiddenVector
    reasoning_template: str


def _clip(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class Persona:
    def __init__(self, cfg: dict, rng: Optional[random.Random] = None):
        self.id: str = cfg['id']
        self.name: str = cfg['name']
        self.risk: str = cfg['risk']
        self.communicativeness: bool = bool(cfg['communicativeness'])
        self.anxiety_sensitivity: float = float(cfg['anxiety_sensitivity'])
        self.exit_sensitivity: float = float(cfg['exit_sensitivity'])
        self.regime_awareness_growth: float = float(cfg['regime_awareness_growth'])
        iv = cfg['initial_vector']
        self._initial_vector = HiddenVector(**{k: float(v) for k, v in iv.items()})
        self._base_weights: dict = {k: float(v) for k, v in cfg['base_weights'].items()}
        self._rng = rng or random.Random()

    def fresh_vector(self) -> HiddenVector:
        return copy.copy(self._initial_vector)

    def update_vector(self, vec: HiddenVector, ctx: MarketContext, checkpoint_idx: int) -> HiddenVector:
        REGIME_ANXIETY_MULT = {
            'bull': 0.30, 'range': 0.70, 'transition': 0.90,
            'volatile': 1.20, 'bear': 1.30, 'crisis': 1.60, 'unclassified': 1.00,
        }
        REGIME_TRUST_DELTA = {
            'bull': +0.020, 'range': -0.005, 'transition': -0.010,
            'volatile': -0.025, 'bear': -0.030, 'crisis': -0.050, 'unclassified': -0.010,
        }
        drawdown_severity = max(0.0, -ctx.drawdown)
        mult = REGIME_ANXIETY_MULT.get(ctx.regime_group, 1.0)
        pressure = drawdown_severity * mult * self.anxiety_sensitivity
        new_anxiety = _clip(vec.anxiety * 0.88 + pressure * 0.12 + 0.005)

        trust_delta = REGIME_TRUST_DELTA.get(ctx.regime_group, -0.010)
        new_trust = _clip(vec.trust + trust_delta)

        new_mu = _clip(vec.market_understanding + 0.001)
        new_ra = _clip(vec.regime_awareness + self.regime_awareness_growth)

        time_factor = min(1.0, checkpoint_idx / 52.0)
        ep = new_anxiety * 0.45 + (1.0 - new_trust) * 0.35 + time_factor * 0.20
        new_ep = _clip(ep * self.exit_sensitivity)

        return HiddenVector(
            anxiety=new_anxiety,
            trust=new_trust,
            market_understanding=new_mu,
            regime_awareness=new_ra,
            exit_propensity=new_ep,
        )

    def select_action(self, vec: HiddenVector, ctx: MarketContext, recent_actions: list) -> str:
        weights = dict(self._base_weights)

        if not self.communicativeness:
            for a in CHAT_ACTIONS - {'activate'}:
                weights[a] = 0.0

        if vec.anxiety > 0.65 and self.communicativeness:
            weights['new_message'] = weights.get('new_message', 0.0) * 2.5
            weights['complain'] = weights.get('complain', 0.0) * 2.0
        if vec.exit_propensity > 0.70:
            weights['deactivate_strategy'] = weights.get('deactivate_strategy', 0.0) * 3.5
        if vec.exit_propensity > 0.55 and self.communicativeness:
            weights['leave_chat'] = weights.get('leave_chat', 0.0) * 2.0

        if ctx.regime_group == 'bull':
            weights['add_strategy'] = weights.get('add_strategy', 0.0) * 2.0
            weights['activate'] = weights.get('activate', 0.0) * 1.5
        if ctx.regime_group in ('crisis', 'bear') and ctx.drawdown < -0.35:
            weights['deactivate_strategy'] = weights.get('deactivate_strategy', 0.0) * 2.0
            weights['change_capital'] = weights.get('change_capital', 0.0) * 0.5

        if vec.regime_awareness > 0.70 and vec.market_understanding > 0.60:
            weights['change_capital'] = weights.get('change_capital', 0.0) * 1.5
            weights['ask_followup'] = weights.get('ask_followup', 0.0) * 1.3

        if 'deactivate_strategy' in recent_actions[-2:]:
            weights['deactivate_strategy'] = 0.0
        if 'leave_chat' in recent_actions[-2:]:
            weights['leave_chat'] = 0.0

        items = [(a, w) for a, w in weights.items() if w > 0]
        if not items:
            return SILENCE
        actions_list, w_list = zip(*items)
        total = sum(w_list)
        r = self._rng.random() * total
        cumsum = 0.0
        for a, w in zip(actions_list, w_list):
            cumsum += w
            if r <= cumsum:
                return a
        return SILENCE

    def decide(
        self,
        vec: HiddenVector,
        ctx: MarketContext,
        checkpoint_idx: int,
        recent_actions: list,
    ) -> DecisionResult:
        new_vec = self.update_vector(vec, ctx, checkpoint_idx)
        action = self.select_action(new_vec, ctx, recent_actions)
        dd_pct = f"{-ctx.drawdown * 100:.1f}"
        reasoning = (
            f"[{self.name}] regime={ctx.regime_group} dd=-{dd_pct}% "
            f"anx={new_vec.anxiety:.2f} trust={new_vec.trust:.2f} ep={new_vec.exit_propensity:.2f} "
            f"-> {action}"
        )
        return DecisionResult(action=action, vector=new_vec, reasoning_template=reasoning)


def load_personas(rng: Optional[random.Random] = None) -> list:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    seed_rng = rng or random.Random()
    return [Persona(p, random.Random(seed_rng.randint(0, 2**31))) for p in cfg['personas']]
