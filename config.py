"""
╔══════════════════════════════════════════════════════════════════════╗
║   THERMODYNAMIC ARROW OF TIME  |  S&P 500 MARKET ENTROPY ENGINE    ║
║   config.py  —  global constants, theme, colormaps, universe        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.colors import LinearSegmentedColormap

# ═══════════════════════════════════════════════════════════════════════
# STOCK UNIVERSE  —  30 S&P 500 stocks, 6 sectors × 5 stocks
# ═══════════════════════════════════════════════════════════════════════
SECTORS = {
    "TECHNOLOGY":  ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "FINANCIALS":  ["JPM",  "BAC",  "GS",   "MS",    "C"   ],
    "HEALTHCARE":  ["JNJ",  "UNH",  "PFE",  "ABBV",  "MRK" ],
    "ENERGY":      ["XOM",  "CVX",  "COP",  "SLB",   "EOG" ],
    "CONSUMER":    ["AMZN", "TSLA", "HD",   "MCD",   "NKE" ],
    "INDUSTRIALS": ["GE",   "CAT",  "BA",   "RTX",   "HON" ],
}

TICKERS = [t for tickers in SECTORS.values() for t in tickers]

TICKER_SECTOR = {
    t: s for s, tickers in SECTORS.items() for t in tickers
}

# Assets ordered for 3-D surface Y-axis (sector-grouped)
ASSET_ORDER = TICKERS   # already sector-grouped

# ═══════════════════════════════════════════════════════════════════════
# SECTOR COLOURS
# ═══════════════════════════════════════════════════════════════════════
SECTOR_COLORS = {
    "TECHNOLOGY":  "#00f2ff",
    "FINANCIALS":  "#ff9500",
    "HEALTHCARE":  "#00ff41",
    "ENERGY":      "#ffd400",
    "CONSUMER":    "#ff1493",
    "INDUSTRIALS": "#bb66ff",
}

# ═══════════════════════════════════════════════════════════════════════
# BLOOMBERG DARK THEME  —  full quant.traderr spec
# ═══════════════════════════════════════════════════════════════════════
THEME = {
    "BG":         "#000000",
    "PANEL_BG":   "#0a0a0a",
    "GRID":       "#1a1a1a",
    "SPINE":      "#333333",
    "TEXT":       "#ffffff",
    "TEXT_DIM":   "#aaaaaa",
    "ORANGE":     "#ff9500",
    "ORANGE_HOT": "#ff6b00",
    "CYAN":       "#00f2ff",
    "YELLOW":     "#ffd400",
    "GREEN":      "#00ff41",
    "RED":        "#ff3050",
    "MAGENTA":    "#ff1493",
    "PINK":       "#ff2a9e",
    "BLUE":       "#00bfff",
    "PURPLE":     "#bb66ff",
    "FONT":       "DejaVu Sans",
}

# ═══════════════════════════════════════════════════════════════════════
# THERMODYNAMIC COLORMAP
#  Low  σ ≈ 0   →  deep black  (time-symmetric, calm market)
#  Mid  σ ≈ 0.3 →  deep red → orange  (building irreversibility)
#  High σ ≈ 1   →  bright yellow-white (crisis, strong arrow of time)
# ═══════════════════════════════════════════════════════════════════════
CMAP_THERMO = LinearSegmentedColormap.from_list(
    "thermo_entropy",
    [
        "#000000",   # 0.00  — void black   (reversible / calm)
        "#1a0020",   # 0.12  — deep purple
        "#4a0030",   # 0.22  — dark crimson
        "#8b0000",   # 0.35  — dark red
        "#ff3050",   # 0.50  — neon red      ← brand RED
        "#ff6b00",   # 0.65  — orange-hot    ← brand ORANGE_HOT
        "#ff9500",   # 0.78  — orange        ← brand ORANGE
        "#ffd400",   # 0.90  — yellow        ← brand YELLOW
        "#ffffff",   # 1.00  — white-hot     (maximum irreversibility)
    ],
    N=512,
)

# VIX-ridge colourmap  (cyan glow)
CMAP_VIX = LinearSegmentedColormap.from_list(
    "vix_glow",
    ["#003344", "#00f2ff", "#ffffff"],
    N=128,
)

# ═══════════════════════════════════════════════════════════════════════
# PIPELINE CONFIG
# ═══════════════════════════════════════════════════════════════════════
CONFIG = {
    # ── Data
    "T_DAYS":       504,    # 2 trading years of daily returns
    "SEED":         42,

    # ── Engine  (entropy production)
    "WINDOW":       40,     # rolling window width  (trading days)
    "N_BINS":       25,     # histogram bins for KL divergence
    "KDE_BW":       0.004,  # KDE bandwidth (fraction of return range)
    "SUBSAMPLE":    72,     # number of time-points on 3-D surface

    # ── Output
    "OUT_DIR":      "outputs",
    "STATIC_PNG":   "outputs/thermo_arrow_of_time.png",
    "ANIM_GIF":     "outputs/thermo_animation.gif",
    "DPI":          100,
    "FIG_SIZE":     (19.2, 10.8),

    # ── Animation
    "GIF_DPI":      80,
    "GIF_FPS":      10,
}

os.makedirs(CONFIG["OUT_DIR"], exist_ok=True)
