"""
CLI entry point.
Usage: python -m harness.run [--personas P1 P2] [--windows W1 W2] [--seed N]
                              [--exchange whitebit|binance] [--max-checkpoints N] [--out PATH]
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.data_sources import DATA_DIR
from harness.point_generator import generate_dataset


def main():
    parser = argparse.ArgumentParser(description='Synthetic trader harness')
    parser.add_argument('--personas', nargs='+', default=None)
    parser.add_argument('--windows', nargs='+', default=None)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--exchange', default='whitebit', choices=['whitebit', 'binance'])
    parser.add_argument('--max-checkpoints', type=int, default=None)
    parser.add_argument('--out', type=str, default=None)
    args = parser.parse_args()

    rows = generate_dataset(
        exchange=args.exchange,
        persona_ids=args.personas,
        window_ids=args.windows,
        seed=args.seed,
        max_checkpoints=args.max_checkpoints,
    )

    if not rows:
        print("No rows generated. Check windows and regime data coverage.")
        sys.exit(1)

    df = pd.DataFrame(rows)
    print(f"\nDataset shape: {df.shape}")
    print("\nAction distribution:")
    print(df['action'].value_counts().to_string())
    print("\nPersona distribution:")
    print(df['persona_id'].value_counts().to_string())

    if args.out:
        out_path = Path(args.out)
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        runs_dir = DATA_DIR / 'runs'
        runs_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        tag = f"s{args.seed}_x{args.exchange}"
        out_path = runs_dir / f"harness_{ts}_{tag}.parquet"

    df.to_parquet(out_path, index=False)
    print(f"\nWritten: {out_path}  ({out_path.stat().st_size // 1024} KB)")


if __name__ == '__main__':
    main()
