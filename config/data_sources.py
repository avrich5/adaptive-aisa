"""Single source of truth for data paths. Working machine = skufs."""
from pathlib import Path

PARQUET_ROOT = Path.home() / "wbprd_skufs" / "base-states" / "data" / "parquet"
ASSETS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "ADA"]
EXCHANGES = ["whitebit", "binance"]

def ohlcv_path(asset: str, exchange: str = "whitebit") -> Path:
    return PARQUET_ROOT / exchange / f"{asset}_USDT_1d.parquet"
