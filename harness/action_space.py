"""Action space constants. Closed set — only what is actually logged in prod."""

CHAT_ACTIONS = frozenset([
    'new_message', 'click_card', 'activate', 'ask_followup',
    'ignore', 'leave_chat', 'complain',
])
EXCHANGE_ACTIONS = frozenset([
    'change_capital', 'deactivate_strategy', 'pause_strategy', 'add_strategy',
])
SILENCE = 'silence'
ALL_ACTIONS = CHAT_ACTIONS | EXCHANGE_ACTIONS | {SILENCE}

# Actions that terminate the run (irreversible exit)
TERMINAL_ACTIONS = frozenset(['deactivate_strategy', 'leave_chat'])

REGIME_GROUPS = {
    'R1_BULL_TREND': 'bull',
    'R2_BEAR_TREND': 'bear',
    'R3_RANGE': 'range',
    'R4_HIGH_VOLATILITY': 'volatile',
    'R5_LOW_VOLATILITY': 'range',
    'R6_ACCUMULATION': 'bear',
    'R7_DISTRIBUTION': 'bear',
    'R8_CAPITULATION': 'crisis',
    'R9_SPECULATIVE_MANIA': 'crisis',
    'R10_LIQUIDITY_STRESS': 'crisis',
    'R11_STRUCTURAL_TRANSITION': 'transition',
    'R12_REGIME_TRANSITION': 'transition',
    'UNCLASSIFIED': 'unclassified',
}

# Regimes that pass gates (UNCLASSIFIED handled explicitly by gates.py)
VALID_REGIMES = frozenset(k for k in REGIME_GROUPS if k != 'UNCLASSIFIED')
