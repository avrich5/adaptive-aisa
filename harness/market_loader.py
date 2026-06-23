"""Load regime context from all_regimes.parquet for a given asset and date."""
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.data_sources import regime_path
from harness.action_space import REGIME_GROUPS, VALID_REGIMES


@dataclass
class MarketContext:
    date: str
    asset: str
    regime: str            # e.g. R1_BULL_TREND
    regime_group: str      # bull / bear / range / volatile / crisis / transition / unclassified
    drawdown: float        # fraction -1.0..0.0 (drawdown_from_high / 100)
    close_price: float
    is_valid: bool         # False when UNCLASSIFIED (gates reject by default)


class MarketLoader:
    def __init__(self, exchange: str = 'whitebit'):
        self.exchange = exchange
        self._by_asset: dict = {}

    def load(self) -> None:
        path = regime_path(self.exchange)
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        for asset_key in df['asset'].unique():
            sub = df[df['asset'] == asset_key].copy()
            sub = sub[~sub.index.duplicated(keep='last')].sort_index()
            self._by_asset[asset_key] = sub

    def get_context(self, asset: str, date) -> Optional[MarketContext]:
        asset_key = asset + 'USDT'
        ts = pd.Timestamp(date)
        sub = self._by_asset.get(asset_key)
        if sub is None:
            return None
        if ts in sub.index:
            row = sub.loc[ts]
        else:
            pos = sub.index.searchsorted(ts)
            pos = min(pos, len(sub) - 1)
            row = sub.iloc[pos]
        regime = str(row['regime'])
        raw_dd = row.get('drawdown_from_high', 0.0)
        drawdown = float(raw_dd) / 100.0 if pd.notna(raw_dd) else 0.0
        return MarketContext(
            date=str(date),
            asset=asset,
            regime=regime,
            regime_group=REGIME_GROUPS.get(regime, 'unclassified'),
            drawdown=drawdown,
            close_price=float(row['close']),
            is_valid=regime in VALID_REGIMES,
        )


def get_weekly_dates(start_date: str, end_date: str) -> list:
    """Weekly checkpoint dates every 7 days between start and end."""
    dates = pd.date_range(start=start_date, end=end_date, freq='7D')
    return [d.strftime('%Y-%m-%d') for d in dates]
