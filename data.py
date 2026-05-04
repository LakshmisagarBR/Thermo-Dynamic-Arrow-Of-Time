"""
╔══════════════════════════════════════════════════════════════════════╗
║   THERMODYNAMIC ARROW OF TIME  |  S&P 500 MARKET ENTROPY ENGINE    ║
║   data.py  —  MODULE 1: DATA                                         ║
║                                                                      ║
║  Generates 504-day synthetic S&P 500 returns with:                  ║
║    • Cholesky-correlated sector block structure                      ║
║    • GARCH(1,1)-style volatility clustering per stock                ║
║    • Two embedded market stress regimes (volatility spikes)          ║
║    • Calibrated to 2022-2024 S&P 500 realized parameters            ║
║                                                                      ║
║  Also computes:                                                      ║
║    • VIX proxy  = cross-sectional realised vol (21-day rolling)     ║
║    • Date index for axis labelling                                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
from datetime import datetime
from config import (TICKERS, TICKER_SECTOR, SECTORS, CONFIG)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  DATA  |  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# SECTOR CORRELATION BLOCK  (6×6, calibrated)
# ═══════════════════════════════════════════════════════════════════════
_SECTOR_CORR = np.array([
    # TECH   FIN    HLT    ENR    CON    IND
    [1.00,  0.52,  0.38,  0.22,  0.61,  0.48],
    [0.52,  1.00,  0.34,  0.30,  0.44,  0.50],
    [0.38,  0.34,  1.00,  0.18,  0.35,  0.33],
    [0.22,  0.30,  0.18,  1.00,  0.25,  0.32],
    [0.61,  0.44,  0.35,  0.25,  1.00,  0.45],
    [0.48,  0.50,  0.33,  0.32,  0.45,  1.00],
])

_SECTOR_LIST  = list(SECTORS.keys())
_SECTOR_IDX   = {s: i for i, s in enumerate(_SECTOR_LIST)}

# Per-sector base annualised vol
_SECTOR_VOL = {
    "TECHNOLOGY":  0.32,
    "FINANCIALS":  0.26,
    "HEALTHCARE":  0.22,
    "ENERGY":      0.34,
    "CONSUMER":    0.28,
    "INDUSTRIALS": 0.24,
}

# Per-ticker idiosyncratic vol spread (additive)
_TICKER_SPREAD = {
    "AAPL":-0.04,"MSFT":-0.06,"NVDA": 0.14,"GOOGL":-0.02,"META": 0.08,
    "JPM": -0.03,"BAC":  0.04,"GS":   0.06,"MS":   0.05, "C":   0.07,
    "JNJ": -0.06,"UNH":  0.02,"PFE":  0.06,"ABBV": 0.04, "MRK":-0.02,
    "XOM": -0.04,"CVX": -0.03,"COP":  0.06,"SLB":  0.12, "EOG": 0.09,
    "AMZN": 0.08,"TSLA": 0.22,"HD":  -0.04,"MCD": -0.08, "NKE": 0.03,
    "GE":   0.06,"CAT":  0.04,"BA":   0.12,"RTX": -0.02, "HON":-0.03,
}

# GARCH(1,1) parameters (approximate S&P 500 calibration)
_GARCH_OMEGA  = 0.000004   # long-run variance contribution
_GARCH_ALPHA  = 0.09       # innovation coefficient
_GARCH_BETA   = 0.88       # persistence


def _build_corr_matrix(tickers):
    """Build 30×30 correlation matrix from sector block structure."""
    N   = len(tickers)
    rng = np.random.default_rng(CONFIG["SEED"])
    rho = np.eye(N)

    for i, ti in enumerate(tickers):
        for j, tj in enumerate(tickers):
            if i >= j:
                continue
            si = TICKER_SECTOR.get(ti, _SECTOR_LIST[0])
            sj = TICKER_SECTOR.get(tj, _SECTOR_LIST[0])
            base = (0.68 if si == sj
                    else _SECTOR_CORR[_SECTOR_IDX[si], _SECTOR_IDX[sj]])
            noise = 0.06 * (rng.random() - 0.5)
            rho[i, j] = rho[j, i] = np.clip(base + noise, -0.9, 0.95)

    # Nearest positive-definite
    ev, evec = np.linalg.eigh(rho)
    ev       = np.maximum(ev, 1e-8)
    rho      = evec @ np.diag(ev) @ evec.T
    d        = np.sqrt(np.diag(rho))
    rho      = rho / np.outer(d, d)
    np.fill_diagonal(rho, 1.0)
    return rho


def _garch_vol_path(T, base_daily_vol, rng, stress_days=None):
    """
    Simulate a GARCH(1,1) conditional volatility path.
    stress_days: list of (start, end, multiplier) tuples to inject vol spikes.
    """
    omega = _GARCH_OMEGA
    alpha = _GARCH_ALPHA
    beta  = _GARCH_BETA
    h     = np.full(T, base_daily_vol ** 2)

    for t in range(1, T):
        eps    = rng.standard_normal()
        innov  = (h[t-1] ** 0.5) * eps
        h[t]   = omega + alpha * innov**2 + beta * h[t-1]
        h[t]   = np.clip(h[t], 1e-8, (0.25)**2 / 252)

    sigma = np.sqrt(h)

    # Inject stress regimes
    if stress_days:
        for start, end, mult in stress_days:
            sigma[start:end] *= mult

    return sigma


def fetch_all():
    """
    Generate calibrated synthetic market data.

    Returns dict with keys:
        returns    : pd.DataFrame  (T×N  log returns)
        dates      : pd.DatetimeIndex
        vix_proxy  : np.ndarray   (T,) — cross-sectional realised vol (annualised)
        tickers    : list[str]
    """
    rng = np.random.default_rng(CONFIG["SEED"])
    T   = CONFIG["T_DAYS"]
    N   = len(TICKERS)

    log(f"Building calibrated synthetic returns  [{N} stocks × {T} days] ...")

    # ── Correlation matrix
    rho = _build_corr_matrix(TICKERS)
    L   = np.linalg.cholesky(rho)

    # ── Stress regimes embedded in the data
    #   Regime 1: days 90–120   (mild correction, ~Mar 2023 analogue)
    #   Regime 2: days 310–360  (sharp crash, ~Oct 2023 analogue)
    stress_days = [(90, 120, 2.8), (310, 360, 4.2)]

    # ── Per-ticker GARCH vol paths
    base_vols = np.array([
        (_SECTOR_VOL[TICKER_SECTOR[t]] + _TICKER_SPREAD.get(t, 0.0)) / np.sqrt(252)
        for t in TICKERS
    ])
    daily_sigma = np.column_stack([
        _garch_vol_path(T, base_vols[i], rng, stress_days)
        for i in range(N)
    ])   # shape (T, N)

    # ── Correlated innovations
    Z      = rng.standard_normal((T, N))
    Z_corr = Z @ L.T   # (T, N) correlated standard normals

    # ── Drift (annualised, calibrated)
    _DRIFT = {
        "TECHNOLOGY": 0.18, "FINANCIALS": 0.10,
        "HEALTHCARE": 0.08, "ENERGY": 0.12,
        "CONSUMER":   0.14, "INDUSTRIALS": 0.09,
    }
    mu_daily = np.array([_DRIFT[TICKER_SECTOR[t]] / 252 for t in TICKERS])

    # ── Log returns  r_t = (μ - σ²/2)dt + σ·dW
    log_rets = ((mu_daily - 0.5 * daily_sigma**2)
                + daily_sigma * Z_corr)   # (T, N)

    # ── Date index
    end_date = datetime(2024, 12, 31)
    dates    = pd.bdate_range(end=end_date, periods=T)
    returns  = pd.DataFrame(log_rets, index=dates, columns=TICKERS)

    # ── VIX proxy  =  21-day rolling cross-sectional realised vol (annualised)
    rolling_var = (returns ** 2).rolling(21, min_periods=5).mean()
    vix_proxy   = np.sqrt(rolling_var.mean(axis=1).values * 252)
    vix_proxy   = np.nan_to_num(vix_proxy, nan=np.nanmean(vix_proxy))

    log(f"Returns  shape={returns.shape}  "
        f"[{returns.index[0].date()} -> {returns.index[-1].date()}]")
    log(f"VIX proxy  min={vix_proxy.min():.3f}  "
        f"max={vix_proxy.max():.3f}  mean={vix_proxy.mean():.3f}")

    return {
        "returns":   returns,
        "dates":     dates,
        "vix_proxy": vix_proxy,
        "tickers":   TICKERS,
    }
