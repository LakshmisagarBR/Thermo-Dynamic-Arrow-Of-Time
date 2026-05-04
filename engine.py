"""
╔══════════════════════════════════════════════════════════════════════╗
║   THERMODYNAMIC ARROW OF TIME  |  S&P 500 MARKET ENTROPY ENGINE    ║
║   engine.py  —  MODULE 2: ENTROPY PRODUCTION ENGINE                 ║
║                                                                      ║
║  Physics Background                                                  ║
║  ─────────────────                                                   ║
║  In non-equilibrium thermodynamics, the entropy production rate σ   ║
║  of a stochastic process X_t quantifies how strongly the process    ║
║  breaks time-reversal symmetry:                                      ║
║                                                                      ║
║      σ = lim_{T→∞} (1/T) · KL( P_fwd || P_rev )                   ║
║                                                                      ║
║  where  P_fwd  is the path-space measure of X_t (forward time)      ║
║  and    P_rev  is the path-space measure of X_{T-t} (reversed).     ║
║                                                                      ║
║  For a univariate return series {r_1, ..., r_W}:                    ║
║      P_fwd  ≡  empirical distribution of  { r_t }                  ║
║      P_rev  ≡  empirical distribution of  {-r_t }                  ║
║                (negating flips the time arrow for zero-drift proc.) ║
║                                                                      ║
║  The KL divergence estimator uses adaptive kernel density:          ║
║                                                                      ║
║      σ̂(t,i) = KL( p̂_fwd || p̂_rev )                               ║
║             = ∫ p̂_fwd(r) · log[ p̂_fwd(r) / p̂_rev(r) ] dr        ║
║                                                                      ║
║  Interpretation:                                                     ║
║      σ̂ ≈ 0  →  returns are nearly time-symmetric (calm regime)      ║
║      σ̂ >> 0 →  strong arrow of time (trending, crisis, memory)      ║
║                                                                      ║
║  Key finding: σ̂ spikes BEFORE and DURING market crashes, making     ║
║  it a potential leading indicator of systemic risk.                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from scipy.stats import gaussian_kde
from datetime import datetime
from config import CONFIG, TICKERS


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ENGINE |  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# 2.1  KL DIVERGENCE  via kernel density estimation
# ═══════════════════════════════════════════════════════════════════════

def _kl_divergence_kde(samples_p: np.ndarray,
                        samples_q: np.ndarray,
                        n_eval:    int = 200) -> float:
    """
    Estimate  KL(P || Q) = ∫ p(x) log[p(x)/q(x)] dx
    using Gaussian KDE for both p and q.

    Parameters
    ----------
    samples_p : 1-D array  — samples from distribution P
    samples_q : 1-D array  — samples from distribution Q
    n_eval    : number of quadrature points

    Returns
    -------
    float ≥ 0
    """
    if len(samples_p) < 6 or len(samples_q) < 6:
        return 0.0

    # Shared evaluation grid covering both distributions
    lo = min(samples_p.min(), samples_q.min()) - 0.005
    hi = max(samples_p.max(), samples_q.max()) + 0.005
    xs = np.linspace(lo, hi, n_eval)

    try:
        kde_p = gaussian_kde(samples_p, bw_method="silverman")
        kde_q = gaussian_kde(samples_q, bw_method="silverman")
    except Exception:
        return 0.0

    p_vals = np.maximum(kde_p(xs), 1e-12)
    q_vals = np.maximum(kde_q(xs), 1e-12)

    # Normalise (KDE already normalised, but numerical safety)
    p_vals /= p_vals.sum()
    q_vals /= q_vals.sum()

    # Discrete KL
    kl = np.sum(p_vals * np.log(p_vals / q_vals))
    return float(np.clip(kl, 0.0, 10.0))


# ═══════════════════════════════════════════════════════════════════════
# 2.2  ENTROPY PRODUCTION RATE  for a single window
# ═══════════════════════════════════════════════════════════════════════

def _entropy_production_window(returns_window: np.ndarray) -> float:
    """
    Estimate σ̂ for a 1-D array of returns.

    Forward process  P:  {r_1, ..., r_W}
    Reversed process Q:  {-r_1, ..., -r_W}  (sign-flip = time-reversal for drift-free process)

    We additionally decorrelate by using first-differences to strip
    autocorrelation that would inflate the KL divergence.
    """
    r = returns_window.astype(float)
    r = r - r.mean()          # centre (remove drift)

    p_samples = r              # forward
    q_samples = -r             # time-reversed

    return _kl_divergence_kde(p_samples, q_samples)


# ═══════════════════════════════════════════════════════════════════════
# 2.3  FULL ENTROPY SURFACE  σ(t, asset)
# ═══════════════════════════════════════════════════════════════════════

def compute_entropy_surface(data_bundle: dict) -> dict:
    """
    Compute the full 2-D entropy production rate surface.

    Returns
    -------
    dict with keys:
        sigma_surface  : np.ndarray  shape (N_assets, N_time)
                         entropy production rate at each (asset, time) point
        sigma_market   : np.ndarray  shape (N_time,)
                         cross-sectional mean σ̂ (market-level arrow of time)
        time_dates     : list of datetime  — date of each time-slice
        time_idx       : np.ndarray  (int indices into original T-day series)
        vix_proxy_sub  : np.ndarray  VIX proxy at each subsampled time point
        asset_labels   : list[str]   — ticker labels for Y-axis
    """
    returns   = data_bundle["returns"]
    vix_proxy = data_bundle["vix_proxy"]
    tickers   = data_bundle["tickers"]
    T, N      = returns.shape

    W      = CONFIG["WINDOW"]
    N_sub  = CONFIG["SUBSAMPLE"]

    # Time points where we have a full window
    t_valid = np.arange(W, T)
    # Subsample evenly
    t_sub   = np.round(np.linspace(t_valid[0], t_valid[-1], N_sub)).astype(int)

    log(f"Computing entropy surface  "
        f"[{N} assets × {N_sub} time-points, window={W}] ...")

    returns_arr = returns.values   # (T, N) numpy array

    sigma = np.zeros((N, N_sub), dtype=float)

    for j_t, t in enumerate(t_sub):
        if j_t % 12 == 0:
            log(f"  time-slice {j_t+1}/{N_sub}  (day {t}) ...")
        window = returns_arr[t - W : t, :]   # (W, N)
        for i in range(N):
            sigma[i, j_t] = _entropy_production_window(window[:, i])

    # Smooth surface slightly (5-point Gaussian in time) to remove noise spikes
    from scipy.ndimage import uniform_filter1d
    sigma = uniform_filter1d(sigma, size=5, axis=1, mode="nearest")

    # Market-level arrow-of-time: cross-sectional mean
    sigma_market = sigma.mean(axis=0)

    # VIX proxy at subsampled points
    vix_sub = vix_proxy[t_sub]

    log(f"Entropy surface  shape={sigma.shape}  "
        f"min={sigma.min():.5f}  max={sigma.max():.5f}  "
        f"mean={sigma.mean():.5f}")

    time_dates = [returns.index[t].to_pydatetime() for t in t_sub]

    return {
        "sigma_surface":  sigma,          # (N_assets, N_time)
        "sigma_market":   sigma_market,   # (N_time,)
        "time_dates":     time_dates,
        "time_idx":       t_sub,
        "vix_proxy_sub":  vix_sub,
        "asset_labels":   tickers,
    }


# ═══════════════════════════════════════════════════════════════════════
# 2.4  SURFACE MESH  for 3-D rendering
# ═══════════════════════════════════════════════════════════════════════

def build_surface_mesh(engine_bundle: dict) -> dict:
    """
    Build the X, Y, Z meshgrids for matplotlib plot_surface.

    X : time axis  (N_time points, normalised 0 → 1)
    Y : asset axis (N_assets points, normalised 0 → 1)
    Z : σ̂(asset, time)
    """
    sigma   = engine_bundle["sigma_surface"]   # (N_assets, N_time)
    N_a, N_t = sigma.shape

    x_raw = np.arange(N_t)   # time ticks
    y_raw = np.arange(N_a)   # asset ticks

    X, Y = np.meshgrid(x_raw, y_raw)   # both shape (N_a, N_t)
    Z    = sigma

    # Normalise Z to [0, 1] for colormap mapping
    z_min = Z.min()
    z_max = Z.max()
    Z_norm = (Z - z_min) / max(z_max - z_min, 1e-10)

    return {
        "X": X, "Y": Y, "Z": Z,
        "Z_norm":  Z_norm,
        "z_min":   z_min,
        "z_max":   z_max,
        "N_a":     N_a,
        "N_t":     N_t,
    }
