"""Single source of truth for data paths. Working machine = skufs."""
from pathlib import Path

# parquet/ = СИРОВИНА (вхід pipeline): тільки OHLCV, без regime.
# pipeline_output/all_regimes.parquet = ВИХІД pipeline: OHLCV + regime (R1-R12) + features.
# Харнес бере КОНТЕКСТ (regime, drawdown_from_high, фічі) з regime_path(), НЕ з ohlcv_path().

PARQUET_ROOT = Path.home() / "wbprd_skufs" / "base-states" / "data" / "parquet"
PIPELINE_OUTPUT_ROOT = Path.home() / "wbprd_skufs" / "base-states" / "data" / "pipeline_output"

ASSETS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "ADA"]
EXCHANGES = ["whitebit", "binance"]

DATA_DIR = Path.home() / "adaptive_aisa" / "data"


def ohlcv_path(asset: str, exchange: str = "whitebit") -> Path:
    # СИРОВИНА для pipeline. Для харнесу НЕ використовувати — mode не містить regime.
    return PARQUET_ROOT / exchange / (asset + "_USDT_1d.parquet")


def regime_path(exchange: str = "whitebit") -> Path:
    # ВИХІД pipeline: OHLCV + regime (R1-R12) + adx_pctl/atr_pctl/volume_zscore/drawdown_from_high.
    # Харнес бере контекст звідси.
    #
    # УВАГА 1: all_regimes.parquet на skufs датований 2026-06-03 — ~20 днів застарів.
    # Свіжий отримується прогоном pipeline (Docker Desktop -> docker compose up pipeline),
    # НЕ копіюванням з іншої машини.
    #
    # УВАГА 2: в колонці regime є UNCLASSIFIED (~1764 рядків) і R12_REGIME_TRANSITION.
    # Харнес повинен явно вирішити — фільтрувати їх чи включати (відповідно до Level 3 / R12-as-buffer).
    # Не мовчати: якщо рядок потрапляє в харнес з UNCLASSIFIED — gate повинен відхилити або позначити.
    return PIPELINE_OUTPUT_ROOT / exchange / "all_regimes.parquet"
