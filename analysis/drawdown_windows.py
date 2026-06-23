"""First real pipeline code: read OHLCV, detect drawdown windows per asset.

Drawdown windows are the substrate the harness runs personas through (see
harness/00_PROJECT_DATA_GENERATOR.md sec.7: cover different drawdown TYPES).
This script produces an inventory of real windows from real candles — no mock.

Output: reports/drawdown_windows.md  (one table, windows >= MIN_DD deep).
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.data_sources import ASSETS, ohlcv_path  # noqa: E402

MIN_DD = 0.20          # only windows with >=20% peak-to-trough
EXCHANGE = "whitebit"

def find_windows(close: pd.Series, min_dd: float = MIN_DD):
    """Return list of (peak_date, trough_date, recover_date|None, depth)."""
    running_max = close.cummax()
    dd = close / running_max - 1.0
    windows, in_dd, peak_i, trough_i, trough_v = [], False, None, None, 0.0
    for i in range(len(close)):
        if not in_dd and dd.iloc[i] < 0:
            in_dd, peak_i, trough_i, trough_v = True, i, i, dd.iloc[i]
        elif in_dd:
            if dd.iloc[i] < trough_v:
                trough_i, trough_v = i, dd.iloc[i]
            if dd.iloc[i] >= 0:  # recovered to prior peak
                if -trough_v >= min_dd:
                    windows.append((close.index[peak_i], close.index[trough_i],
                                    close.index[i], -trough_v))
                in_dd = False
    if in_dd and -trough_v >= min_dd:  # still underwater at series end
        windows.append((close.index[peak_i], close.index[trough_i], None, -trough_v))
    return windows

def main():
    out = ["# Drawdown windows inventory", "",
           f"Source: {EXCHANGE} daily OHLCV. Threshold: depth >= {MIN_DD:.0%}.", ""]
    total = 0
    for asset in ASSETS:
        p = ohlcv_path(asset, EXCHANGE)
        if not p.exists():
            out.append(f"## {asset}: MISSING ({p})")
            continue
        df = pd.read_parquet(p)
        wins = find_windows(df["close"])
        total += len(wins)
        out.append(f"## {asset} ({len(df)} candles, {len(wins)} windows)")
        out.append("| peak | trough | recovered | depth | weeks |")
        out.append("|------|--------|-----------|-------|-------|")
        for peak, trough, rec, depth in wins:
            recs = rec.date() if rec is not None else "underwater"
            weeks = round(((rec or df.index[-1]) - peak).days / 7) if hasattr(peak, "date") else "?"
            out.append(f"| {peak.date()} | {trough.date()} | {recs} | {depth:.1%} | {weeks} |")
        out.append("")
    out.insert(3, f"**Total windows found: {total}**")
    out.insert(4, "")
    rep = Path(__file__).resolve().parent.parent / "reports" / "drawdown_windows.md"
    rep.write_text("\n".join(out))
    print(f"wrote {rep} ({total} windows across {len(ASSETS)} assets)")

if __name__ == "__main__":
    main()
