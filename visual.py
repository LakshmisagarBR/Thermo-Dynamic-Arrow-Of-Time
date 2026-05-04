"""
╔══════════════════════════════════════════════════════════════════════╗
║   THERMODYNAMIC ARROW OF TIME  |  S&P 500 MARKET ENTROPY ENGINE    ║
║   visual.py  —  MODULE 3: STATIC IMAGE RENDERER  (1920×1080)        ║
║                                                                      ║
║  Layout: Bloomberg Multi-Panel Dashboard (Type B)                    ║
║                                                                      ║
║  ┌────────────────────────────┬──────────────────────┐              ║
║  │                            │  σ̂ Time Series       │              ║
║  │   3-D Entropy Surface      ├──────────────────────┤              ║
║  │   (main visualization)     │  Sector Risk Bars    │              ║
║  │                            ├──────────────────────┤              ║
║  │   VIX ridge glowing cyan   │  Asset σ̂ Heatmap     │              ║
║  │   Floor shadow contourf    ├──────────────────────┤              ║
║  │   Sector Y-axis labels     │  Distribution Hist   │              ║
║  └────────────────────────────┴──────────────────────┘              ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime

from config import (THEME, CMAP_THERMO, CONFIG,
                    SECTORS, SECTOR_COLORS, TICKER_SECTOR, TICKERS)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] VISUAL |  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# HELPER: style 2-D panel
# ═══════════════════════════════════════════════════════════════════════

def _style(ax, xlabel="", ylabel="", title=""):
    ax.set_facecolor(THEME["PANEL_BG"])
    for sp in ax.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.5)
    ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=8,
                   direction="in", length=3)
    ax.xaxis.grid(True, color=THEME["GRID"], lw=0.3, alpha=0.45)
    ax.yaxis.grid(True, color=THEME["GRID"], lw=0.3, alpha=0.45)
    if xlabel:
        ax.set_xlabel(xlabel, color=THEME["TEXT_DIM"],
                      fontsize=9, fontfamily=THEME["FONT"])
    if ylabel:
        ax.set_ylabel(ylabel, color=THEME["TEXT_DIM"],
                      fontsize=9, fontfamily=THEME["FONT"])
    if title:
        ax.set_title(title, color=THEME["TEXT_DIM"],
                     fontsize=8.5, fontfamily=THEME["FONT"],
                     pad=4, loc="left")


# ═══════════════════════════════════════════════════════════════════════
# 3-D ENTROPY SURFACE
# ═══════════════════════════════════════════════════════════════════════

def _draw_3d_surface(ax3d, mesh, engine_bundle, data_bundle,
                     azim=-55.0, elev=26.0, t_cutoff=None):
    """
    Draw the full 3-D thermodynamic entropy surface.

    t_cutoff: int or None — if set, only render up to time column t_cutoff
              (used by animation to build surface left-to-right)
    """
    X       = mesh["X"]
    Y       = mesh["Y"]
    Z       = mesh["Z"]
    N_a     = mesh["N_a"]
    N_t     = mesh["N_t"]
    z_min   = mesh["z_min"]
    z_max   = mesh["z_max"]

    tc = N_t if t_cutoff is None else max(2, t_cutoff)

    X_s = X[:, :tc]
    Y_s = Y[:, :tc]
    Z_s = Z[:, :tc]

    norm = Normalize(vmin=z_min, vmax=z_max)

    # ── 3-D panes & grid  (quant.traderr spec)
    pane = (0.02, 0.02, 0.02, 1.0)
    ax3d.xaxis.set_pane_color(pane)
    ax3d.yaxis.set_pane_color(pane)
    ax3d.zaxis.set_pane_color(pane)
    for axis in (ax3d.xaxis, ax3d.yaxis, ax3d.zaxis):
        axis._axinfo["grid"]["color"]     = (0.12, 0.12, 0.12, 0.6)
        axis._axinfo["grid"]["linewidth"] = 0.4
    ax3d.set_facecolor(THEME["BG"])

    # ── Main surface
    ax3d.plot_surface(
        X_s, Y_s, Z_s,
        cmap=CMAP_THERMO,
        norm=norm,
        alpha=0.92,
        rstride=1, cstride=1,
        edgecolor=(1.0, 0.58, 0.0, 0.08),
        linewidth=0.22,
        antialiased=True,
        zorder=2,
    )

    # ── Floor contour shadow  (quant.traderr signature)
    z_floor = z_min - 0.25 * (z_max - z_min)
    ax3d.contourf(
        X_s, Y_s, Z_s,
        zdir="z", offset=z_floor,
        cmap=CMAP_THERMO, norm=norm,
        alpha=0.28, levels=14, zorder=1,
    )

    # ── VIX proxy ridge line  (glowing cyan)
    vix_sub = engine_bundle["vix_proxy_sub"][:tc]
    # Normalise VIX to Z scale for overlay
    vix_z   = z_min + (vix_sub / vix_sub.max()) * (z_max - z_min) * 0.85
    x_ridge = np.arange(tc)
    y_ridge = np.full(tc, N_a // 2)   # draw down the middle of asset axis

    # Glow: thick low-alpha + thin bright
    ax3d.plot(x_ridge, y_ridge, vix_z,
              color=THEME["CYAN"], lw=5.0, alpha=0.15,
              solid_capstyle="round", zorder=10)
    ax3d.plot(x_ridge, y_ridge, vix_z,
              color=THEME["CYAN"], lw=1.8, alpha=0.90,
              solid_capstyle="round", zorder=11,
              label="VIX proxy")

    # End-point dot
    ax3d.scatter([x_ridge[-1]], [y_ridge[-1]], [vix_z[-1]],
                 s=36, color=THEME["YELLOW"],
                 edgecolors="white", lw=0.6, zorder=15)

    # ── Market mean σ ridge  (orange)
    sigma_mkt = engine_bundle["sigma_market"][:tc]
    ax3d.plot(np.arange(tc),
              np.full(tc, -0.6),
              sigma_mkt,
              color=THEME["ORANGE"], lw=2.2, alpha=0.85,
              solid_capstyle="round", zorder=10)

    # ── Y-axis sector labels
    sector_list = list(SECTORS.keys())
    n_per       = 5
    for k, sector in enumerate(sector_list):
        y_pos = k * n_per + n_per // 2
        ax3d.text(tc - 1, y_pos, z_max * 1.05,
                  sector[:4],
                  fontsize=7, color=SECTOR_COLORS[sector],
                  ha="left", va="bottom",
                  fontfamily=THEME["FONT"], fontweight="bold", zorder=20)

    # ── Axes appearance
    ax3d.set_xlabel("TIME",   fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=8, fontfamily=THEME["FONT"])
    ax3d.set_ylabel("ASSET",  fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=8, fontfamily=THEME["FONT"])
    ax3d.set_zlabel(r"$\hat{\sigma}$  ENTROPY PRODUCTION",
                    fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=10, fontfamily=THEME["FONT"])
    ax3d.tick_params(colors=THEME["TEXT_DIM"], labelsize=7)

    # Custom Y ticks = sector names
    ytick_pos = [k * n_per + n_per // 2 for k in range(6)]
    ax3d.set_yticks(ytick_pos)
    ax3d.set_yticklabels([s[:4] for s in sector_list],
                          fontsize=6.5, color=THEME["TEXT_DIM"])

    ax3d.set_box_aspect([2.2, 1.0, 0.75])
    ax3d.view_init(elev=elev, azim=azim)


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 1  —  Market-level σ(t) time series
# ═══════════════════════════════════════════════════════════════════════

def _draw_sigma_time(ax, engine_bundle, data_bundle):
    sigma_mkt = engine_bundle["sigma_market"]
    vix_sub   = engine_bundle["vix_proxy_sub"]
    N_t       = len(sigma_mkt)
    xs        = np.arange(N_t)

    # Stress regimes shaded
    for start_frac, end_frac, label in [
        (0.17, 0.25, "STRESS 1"),
        (0.60, 0.73, "STRESS 2"),
    ]:
        x0 = int(start_frac * N_t)
        x1 = int(end_frac   * N_t)
        ax.axvspan(x0, x1, color=THEME["RED"], alpha=0.08)
        ax.text((x0+x1)//2, sigma_mkt.max()*0.9,
                label, ha="center", fontsize=6,
                color=THEME["RED"], fontfamily=THEME["FONT"])

    # Sigma fill + line
    ax.fill_between(xs, sigma_mkt, alpha=0.15, color=THEME["ORANGE"])
    ax.plot(xs, sigma_mkt, color=THEME["ORANGE"], lw=1.6, zorder=4)

    # VIX proxy (rescaled to same axis)
    vix_scaled = vix_sub * (sigma_mkt.max() / vix_sub.max())
    ax.plot(xs, vix_scaled, color=THEME["CYAN"], lw=1.1,
            ls="--", alpha=0.75, label="VIX proxy (scaled)")

    ax.axhline(sigma_mkt.mean(), color=THEME["YELLOW"],
               lw=0.9, ls=":", alpha=0.8)

    _style(ax,
           xlabel="Time (rolling windows)",
           ylabel=r"$\bar{\hat{\sigma}}$",
           title=r"MARKET ENTROPY PRODUCTION  $\bar{\hat{\sigma}}(t)$")

    leg = ax.legend(fontsize=7, facecolor=THEME["BG"],
                    edgecolor=THEME["GRID"])
    for txt in leg.get_texts():
        txt.set_color(THEME["TEXT_DIM"])


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 2  —  Per-sector mean entropy bar chart
# ═══════════════════════════════════════════════════════════════════════

def _draw_sector_entropy(ax, engine_bundle):
    sigma   = engine_bundle["sigma_surface"]   # (N_assets, N_time)
    sectors = list(SECTORS.keys())
    n_per   = 5
    means   = [sigma[k*n_per:(k+1)*n_per, :].mean() for k in range(6)]
    colors  = [SECTOR_COLORS[s] for s in sectors]
    labels  = [s[:4] for s in sectors]

    bars = ax.barh(labels, means, color=colors,
                   edgecolor=THEME["BG"], linewidth=0.4,
                   height=0.55, alpha=0.85)

    for bar, m, col in zip(bars, means, colors):
        ax.scatter([m], [bar.get_y() + bar.get_height()/2],
                   s=20, color=col, edgecolors="white", lw=0.4, zorder=5)

    _style(ax,
           xlabel=r"Mean $\hat{\sigma}$",
           title="SECTOR ENTROPY  (MEAN)")


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 3  —  Asset-level entropy heatmap (mini strip)
# ═══════════════════════════════════════════════════════════════════════

def _draw_asset_heatmap(ax, engine_bundle):
    sigma  = engine_bundle["sigma_surface"]   # (N_assets, N_time)
    N_a    = sigma.shape[0]
    # Subsample time to max 30 columns for readability
    step   = max(1, sigma.shape[1] // 30)
    sigma_s= sigma[:, ::step]

    ax.imshow(sigma_s, aspect="auto", origin="lower",
              cmap=CMAP_THERMO, interpolation="bilinear")

    # Sector dividers
    n_per = 5
    for k in range(1, 6):
        ax.axhline(k * n_per - 0.5, color=THEME["SPINE"], lw=0.6)

    # Y-tick labels = sector names
    ax.set_yticks([k*n_per + n_per//2 for k in range(6)])
    ax.set_yticklabels([s[:4] for s in SECTORS.keys()],
                        fontsize=7, color=THEME["TEXT_DIM"])
    ax.set_facecolor(THEME["PANEL_BG"])
    ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=7,
                   direction="in", length=2)
    ax.set_xlabel("Time →", color=THEME["TEXT_DIM"],
                  fontsize=8, fontfamily=THEME["FONT"])
    ax.set_title(r"ENTROPY HEATMAP  $\hat{\sigma}$(asset, t)",
                 color=THEME["TEXT_DIM"], fontsize=8.5,
                 fontfamily=THEME["FONT"], pad=4, loc="left")
    for sp in ax.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.5)


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 4  —  σ distribution histogram
# ═══════════════════════════════════════════════════════════════════════

def _draw_sigma_dist(ax, engine_bundle):
    sigma_flat = engine_bundle["sigma_surface"].flatten()
    bins = 40

    n, b, patches = ax.hist(sigma_flat, bins=bins,
                             color=THEME["ORANGE_HOT"],
                             edgecolor=THEME["BG"],
                             alpha=0.80, lw=0.2, zorder=3)

    # Colour bars by entropy level: low=dark red, high=yellow
    norm = Normalize(vmin=b[0], vmax=b[-1])
    for patch, left in zip(patches, b[:-1]):
        c = CMAP_THERMO(norm(left + (b[1]-b[0])/2))
        patch.set_facecolor(c)

    ax.axvline(np.mean(sigma_flat), color=THEME["YELLOW"],
               lw=1.3, ls=":", zorder=5)
    ax.axvline(np.percentile(sigma_flat, 95), color=THEME["RED"],
               lw=1.0, ls="--", zorder=5)

    _style(ax,
           xlabel=r"$\hat{\sigma}$",
           ylabel="Count",
           title=r"DISTRIBUTION  $P(\hat{\sigma})$")


# ═══════════════════════════════════════════════════════════════════════
# TITLE BLOCK
# ═══════════════════════════════════════════════════════════════════════

def _draw_title_block(fig, engine_bundle, data_bundle):
    sigma_mkt = engine_bundle["sigma_market"]
    vix_sub   = engine_bundle["vix_proxy_sub"]
    N_a, N_t  = engine_bundle["sigma_surface"].shape
    dates     = data_bundle["dates"]

    date_range = (f"{dates[0].strftime('%b %Y')} – "
                  f"{dates[-1].strftime('%b %Y')}")

    # Main title
    fig.text(0.50, 0.965,
             "THERMODYNAMIC ARROW OF TIME  |  S&P 500 ENTROPY PRODUCTION",
             ha="center", fontsize=23, fontweight="bold",
             color=THEME["ORANGE"], fontfamily=THEME["FONT"])

    # Subtitle / equation
    fig.text(0.50, 0.937,
             r"$\hat{\sigma}(t,i) = \mathrm{KL}\!\left(\,\hat{p}_{\mathrm{fwd}}"
             r"\;\|\;\hat{p}_{\mathrm{rev}}\right)$"
             r"     $p_{\mathrm{rev}}(r) \equiv p(-r)$"
             f"     Window = {CONFIG['WINDOW']} days     [{date_range}]",
             ha="center", fontsize=11, color=THEME["TEXT_DIM"],
             fontfamily=THEME["FONT"])

    # HUD stats
    hud = (f"Assets = {N_a}    "
           f"Time windows = {N_t}    "
           f"σ̂ mean = {sigma_mkt.mean():.5f}    "
           f"σ̂ peak = {sigma_mkt.max():.5f}    "
           f"VIX proxy peak = {vix_sub.max():.3f}")
    fig.text(0.97, 0.907,
             hud,
             ha="right", fontsize=10, fontweight="bold",
             color=THEME["YELLOW"], fontfamily=THEME["FONT"])

    # Sector colour legend
    x0 = 0.06
    for sector, col in SECTOR_COLORS.items():
        fig.text(x0, 0.907, f"■ {sector[:4]}",
                 ha="left", fontsize=8,
                 color=col, fontfamily=THEME["FONT"])
        x0 += 0.088

    # Watermark
    fig.text(0.985, 0.010, "@Laksh",
             ha="right", va="bottom", fontsize=10,
             color=THEME["TEXT_DIM"], fontfamily=THEME["FONT"], alpha=0.6)


# ═══════════════════════════════════════════════════════════════════════
# COLORBAR
# ═══════════════════════════════════════════════════════════════════════

def _draw_colorbar(fig, mesh):
    norm = Normalize(vmin=mesh["z_min"], vmax=mesh["z_max"])
    sm   = ScalarMappable(cmap=CMAP_THERMO, norm=norm)
    sm.set_array([])

    cax  = fig.add_axes([0.034, 0.12, 0.008, 0.38])
    cbar = fig.colorbar(sm, cax=cax, orientation="vertical")
    cbar.ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=7)
    cbar.set_label(r"$\hat{\sigma}$  (entropy production rate)",
                   color=THEME["TEXT_DIM"], fontsize=8,
                   fontfamily=THEME["FONT"], labelpad=6)
    cbar.ax.yaxis.label.set_color(THEME["TEXT_DIM"])
    cbar.ax.text(3.5, 0.02, "REVERSIBLE\n(calm)",
                 color=THEME["TEXT_DIM"], fontsize=6.5, va="bottom")
    cbar.ax.text(3.5, 0.98, "IRREVERSIBLE\n(crisis)",
                 color=THEME["YELLOW"], fontsize=6.5, va="top")


# ═══════════════════════════════════════════════════════════════════════
# MASTER RENDER  —  static PNG
# ═══════════════════════════════════════════════════════════════════════

def render_static(data_bundle, engine_bundle, mesh,
                  out_path=CONFIG["STATIC_PNG"]):
    log("Rendering static image 1920×1080 ...")

    fig = plt.figure(figsize=CONFIG["FIG_SIZE"],
                     dpi=CONFIG["DPI"],
                     facecolor=THEME["BG"])

    gs = gridspec.GridSpec(
        4, 2,
        width_ratios=[2.5, 1],
        left=0.06, right=0.97,
        top=0.88, bottom=0.05,
        hspace=0.44, wspace=0.06,
    )
    ax3d = fig.add_subplot(gs[:, 0], projection="3d")
    ax1  = fig.add_subplot(gs[0, 1])
    ax2  = fig.add_subplot(gs[1, 1])
    ax3  = fig.add_subplot(gs[2, 1])
    ax4  = fig.add_subplot(gs[3, 1])

    _draw_3d_surface(ax3d, mesh, engine_bundle, data_bundle)
    _draw_sigma_time(ax1,  engine_bundle, data_bundle)
    _draw_sector_entropy(ax2, engine_bundle)
    _draw_asset_heatmap(ax3,  engine_bundle)
    _draw_sigma_dist(ax4, engine_bundle)

    _draw_colorbar(fig, mesh)
    _draw_title_block(fig, engine_bundle, data_bundle)

    fig.savefig(out_path, dpi=CONFIG["DPI"],
                facecolor=THEME["BG"], bbox_inches="tight")
    plt.close(fig)
    log(f"Static image saved -> {out_path}")
