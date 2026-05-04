"""
╔══════════════════════════════════════════════════════════════════════╗
║   THERMODYNAMIC ARROW OF TIME  |  S&P 500 MARKET ENTROPY ENGINE    ║
║   animate.py  —  MODULE 4: SMOOTH ANIMATED GIF                      ║
║                                                                      ║
║  Three-phase animation                                               ║
║  ─────────────────────                                               ║
║  PHASE 1  REVEAL   (frames  0-29)                                   ║
║    Surface sweeps in left-to-right as entropy production             ║
║    is "discovered" through time. VIX ridge draws in live.           ║
║    Camera slowly tilts upward from flat to full 3-D angle.          ║
║                                                                      ║
║  PHASE 2  HOLD     (frames 30-44)                                   ║
║    Full surface shown. Camera drifts gently. HUD glows.             ║
║                                                                      ║
║  PHASE 3  ORBIT    (frames 45-99)                                   ║
║    Smooth 360° azimuth orbit around the final surface.              ║
║    Camera elevation rises and falls sinusoidally.                    ║
║    Side panels stay static — only 3-D view rotates.                 ║
║                                                                      ║
║  Total: 100 frames  @ 10 fps  = 10 second loop                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D
import imageio
import io
import os
from datetime import datetime

from config import (THEME, CMAP_THERMO, CONFIG,
                    SECTORS, SECTOR_COLORS, TICKER_SECTOR)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  ANIM  |  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# EASING
# ═══════════════════════════════════════════════════════════════════════

def _ease(t):
    """Smooth-step cubic: derivative = 0 at both ends."""
    return t * t * (3.0 - 2.0 * t)


def _ease_quintic(t):
    """6th-order smooth-step: even smoother acceleration."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


# ═══════════════════════════════════════════════════════════════════════
# PANEL HELPERS  (right-side static panels)
# ═══════════════════════════════════════════════════════════════════════

def _style_mini(ax, title=""):
    ax.set_facecolor(THEME["PANEL_BG"])
    for sp in ax.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.4)
    ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=7,
                   direction="in", length=2)
    ax.yaxis.grid(True, color=THEME["GRID"], lw=0.25, alpha=0.5)
    ax.xaxis.grid(True, color=THEME["GRID"], lw=0.25, alpha=0.5)
    if title:
        ax.set_title(title, color=THEME["TEXT_DIM"],
                     fontsize=7.5, fontfamily=THEME["FONT"],
                     pad=3, loc="left")


def _draw_right_sigma(ax, engine_bundle, t_cutoff):
    """Sigma time-series panel — draws up to t_cutoff."""
    sigma_mkt = engine_bundle["sigma_market"][:t_cutoff]
    vix_sub   = engine_bundle["vix_proxy_sub"][:t_cutoff]
    xs        = np.arange(len(sigma_mkt))
    N_t_full  = len(engine_bundle["sigma_market"])

    ax.fill_between(xs, sigma_mkt, alpha=0.18, color=THEME["ORANGE"])
    ax.plot(xs, sigma_mkt, color=THEME["ORANGE"], lw=1.6, zorder=4)

    if len(vix_sub) > 1:
        vix_sc = vix_sub * (engine_bundle["sigma_market"].max()
                            / engine_bundle["vix_proxy_sub"].max())
        ax.plot(xs, vix_sc, color=THEME["CYAN"], lw=1.1,
                ls="--", alpha=0.75)

    ax.axhline(engine_bundle["sigma_market"].mean(),
               color=THEME["YELLOW"], lw=0.8, ls=":", alpha=0.7)
    ax.set_xlim(0, N_t_full)
    ax.set_ylim(0, engine_bundle["sigma_market"].max() * 1.15)
    _style_mini(ax, title="MARKET ENTROPY  σ(t)")
    ax.set_xlabel("time", color=THEME["TEXT_DIM"],
                  fontsize=7, fontfamily=THEME["FONT"])


def _draw_right_heatmap(ax, engine_bundle, t_cutoff):
    """Mini entropy heatmap up to t_cutoff."""
    sigma  = engine_bundle["sigma_surface"][:, :t_cutoff]
    if sigma.shape[1] < 2:
        ax.set_facecolor(THEME["PANEL_BG"])
        return
    step = max(1, sigma.shape[1] // 28)
    sigma_s = sigma[:, ::step]
    ax.imshow(sigma_s, aspect="auto", origin="lower",
              cmap=CMAP_THERMO, interpolation="bilinear",
              vmin=engine_bundle["sigma_surface"].min(),
              vmax=engine_bundle["sigma_surface"].max())
    n_per = 5
    for k in range(1, 6):
        ax.axhline(k * n_per - 0.5, color=THEME["SPINE"], lw=0.5)
    ax.set_yticks([k*n_per + n_per//2 for k in range(6)])
    ax.set_yticklabels([s[:3] for s in SECTORS.keys()],
                        fontsize=6, color=THEME["TEXT_DIM"])
    ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=6,
                   direction="in", length=2)
    for sp in ax.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.4)
    ax.set_title("ENTROPY HEATMAP", color=THEME["TEXT_DIM"],
                  fontsize=7.5, fontfamily=THEME["FONT"], pad=3, loc="left")


# ═══════════════════════════════════════════════════════════════════════
# CORE FRAME RENDERER
# ═══════════════════════════════════════════════════════════════════════

def _render_frame(engine_bundle, data_bundle, mesh,
                  azim, elev, t_cutoff,
                  phase_label, global_progress,
                  reveal_alpha=1.0):
    """Render one animation frame. Returns H×W×4 numpy RGBA array."""

    N_a, N_t = mesh["N_a"], mesh["N_t"]
    X, Y, Z  = mesh["X"], mesh["Y"], mesh["Z"]
    z_min, z_max = mesh["z_min"], mesh["z_max"]
    norm     = Normalize(vmin=z_min, vmax=z_max)

    fig = plt.figure(figsize=(16.0, 9.0),
                     dpi=CONFIG["GIF_DPI"],
                     facecolor=THEME["BG"])

    gs = gridspec.GridSpec(
        2, 2,
        width_ratios=[2.6, 1],
        left=0.04, right=0.97,
        top=0.87, bottom=0.05,
        hspace=0.42, wspace=0.06,
    )
    ax3d = fig.add_subplot(gs[:, 0], projection="3d")
    ax_s = fig.add_subplot(gs[0, 1])
    ax_h = fig.add_subplot(gs[1, 1])

    # ── 3-D panes
    pane = (0.02, 0.02, 0.02, 1.0)
    ax3d.xaxis.set_pane_color(pane)
    ax3d.yaxis.set_pane_color(pane)
    ax3d.zaxis.set_pane_color(pane)
    for axis in (ax3d.xaxis, ax3d.yaxis, ax3d.zaxis):
        axis._axinfo["grid"]["color"]     = (0.12, 0.12, 0.12, 0.6)
        axis._axinfo["grid"]["linewidth"] = 0.4
    ax3d.set_facecolor(THEME["BG"])
    ax3d.view_init(elev=elev, azim=azim)
    ax3d.set_box_aspect([2.2, 1.0, 0.75])
    ax3d.tick_params(colors=THEME["TEXT_DIM"], labelsize=6)

    tc = max(2, min(t_cutoff, N_t))
    X_s = X[:, :tc]; Y_s = Y[:, :tc]; Z_s = Z[:, :tc]

    # ── Main surface
    ax3d.plot_surface(
        X_s, Y_s, Z_s,
        cmap=CMAP_THERMO, norm=norm,
        alpha=0.90 * reveal_alpha,
        rstride=1, cstride=1,
        edgecolor=(1.0, 0.58, 0.0, 0.07),
        linewidth=0.20, antialiased=True, zorder=2,
    )

    # ── Floor shadow
    z_floor = z_min - 0.22 * (z_max - z_min)
    ax3d.contourf(X_s, Y_s, Z_s,
                  zdir="z", offset=z_floor,
                  cmap=CMAP_THERMO, norm=norm,
                  alpha=0.22 * reveal_alpha, levels=12, zorder=1)

    # ── VIX ridge (cyan)
    vix_sub = engine_bundle["vix_proxy_sub"][:tc]
    vix_z   = z_min + (vix_sub / engine_bundle["vix_proxy_sub"].max()) \
              * (z_max - z_min) * 0.82
    xr = np.arange(tc)
    yr = np.full(tc, N_a // 2)
    ax3d.plot(xr, yr, vix_z, color=THEME["CYAN"],
              lw=4.5, alpha=0.12 * reveal_alpha,
              solid_capstyle="round", zorder=10)
    ax3d.plot(xr, yr, vix_z, color=THEME["CYAN"],
              lw=1.6, alpha=0.88 * reveal_alpha,
              solid_capstyle="round", zorder=11)
    if tc > 1:
        ax3d.scatter([xr[-1]], [yr[-1]], [vix_z[-1]],
                     s=30, color=THEME["YELLOW"],
                     edgecolors="white", lw=0.5, zorder=15)

    # ── Market sigma ridge (orange)
    sm = engine_bundle["sigma_market"][:tc]
    ax3d.plot(np.arange(tc), np.full(tc, -0.6), sm,
              color=THEME["ORANGE"], lw=2.0,
              alpha=0.85 * reveal_alpha,
              solid_capstyle="round", zorder=10)

    # ── Sector labels
    sector_list = list(SECTORS.keys())
    for k, sector in enumerate(sector_list):
        y_pos = k * 5 + 2
        ax3d.text(tc - 1, y_pos, z_max * 1.06,
                  sector[:4],
                  fontsize=6.5, color=SECTOR_COLORS[sector],
                  ha="left", va="bottom",
                  fontfamily=THEME["FONT"], fontweight="bold", zorder=20)

    # Axes labels
    ax3d.set_xlabel("TIME",  fontsize=8, color=THEME["TEXT_DIM"],
                    labelpad=6, fontfamily=THEME["FONT"])
    ax3d.set_ylabel("ASSET", fontsize=8, color=THEME["TEXT_DIM"],
                    labelpad=6, fontfamily=THEME["FONT"])
    ax3d.set_zlabel("σ̂", fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=8, fontfamily=THEME["FONT"])
    ytick_pos = [k*5+2 for k in range(6)]
    ax3d.set_yticks(ytick_pos)
    ax3d.set_yticklabels([s[:4] for s in sector_list],
                          fontsize=6, color=THEME["TEXT_DIM"])

    # ── HUD overlays
    sigma_live = engine_bundle["sigma_market"][:tc]
    live_mean  = sigma_live.mean() if len(sigma_live) else 0.0
    vix_live   = vix_sub[-1] if len(vix_sub) else 0.0

    ax3d.text2D(0.02, 0.97,
                phase_label,
                transform=ax3d.transAxes,
                fontsize=10, color=THEME["ORANGE"],
                fontfamily=THEME["FONT"], fontweight="bold", va="top")

    ax3d.text2D(0.02, 0.90,
                f"σ̂ mean = {live_mean:.5f}",
                transform=ax3d.transAxes,
                fontsize=8, color=THEME["YELLOW"],
                fontfamily=THEME["FONT"], va="top")

    ax3d.text2D(0.98, 0.97,
                f"VIX proxy = {vix_live:.4f}    t = {tc}/{N_t}",
                transform=ax3d.transAxes,
                fontsize=8, color=THEME["CYAN"],
                fontfamily=THEME["FONT"], ha="right", va="top")

    # ── Right panels
    _draw_right_sigma(ax_s, engine_bundle, tc)
    _draw_right_heatmap(ax_h, engine_bundle, tc)

    # ── Title block
    fig.text(0.50, 0.950,
             "THERMODYNAMIC ARROW OF TIME  |  S&P 500",
             ha="center", fontsize=15, fontweight="bold",
             color=THEME["ORANGE"], fontfamily=THEME["FONT"])
    fig.text(0.50, 0.924,
             r"$\hat{\sigma}(t,i) = \mathrm{KL}(\hat{p}_\mathrm{fwd}\,||\,\hat{p}_\mathrm{rev})$"
             r"     $p_\mathrm{rev}(r) \equiv p(-r)$",
             ha="center", fontsize=9,
             color=THEME["TEXT_DIM"], fontfamily=THEME["FONT"])

    # ── Global progress bar
    bar = fig.add_axes([0.04, 0.018, 0.93, 0.012])
    bar.set_facecolor(THEME["PANEL_BG"])
    bar.set_xlim(0, 1); bar.set_ylim(0, 1)
    bar.set_xticks([]); bar.set_yticks([])
    for sp in bar.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.3)
    bar.barh(0.5, 1.0,              height=0.9,
             color=THEME["GRID"],   left=0, align="center")
    bar.barh(0.5, global_progress,  height=0.9,
             color=THEME["ORANGE"], left=0, align="center", alpha=0.7)

    # Phase tick marks on bar
    for frac, lbl in [(0.0,"START"), (0.30,"FULL"), (0.45,"HOLD"), (1.0,"END")]:
        bar.axvline(frac, color=THEME["SPINE"], lw=0.8)
        bar.text(frac, -0.6, lbl, ha="center", va="top",
                 fontsize=5.5, color=THEME["TEXT_DIM"],
                 fontfamily=THEME["FONT"])

    # Watermark
    fig.text(0.985, 0.048, "@quant.traderr",
             ha="right", va="bottom", fontsize=8,
             color=THEME["TEXT_DIM"], fontfamily=THEME["FONT"], alpha=0.6)

    # ── Capture
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=CONFIG["GIF_DPI"],
                facecolor=THEME["BG"])
    plt.close(fig)
    buf.seek(0)
    return np.array(imageio.v3.imread(buf))


# ═══════════════════════════════════════════════════════════════════════
# ANIMATION SCHEDULE
# ═══════════════════════════════════════════════════════════════════════

def _build_schedule(N_t,
                    reveal_frames=30,
                    hold_frames=15,
                    orbit_frames=55):
    """
    Build list of frame parameter dicts.

    Phase 1 REVEAL  : surface sweeps in from t=0 to t=N_t
    Phase 2 HOLD    : full surface, gentle camera drift
    Phase 3 ORBIT   : 360° azimuth rotation
    """
    schedule = []
    total = reveal_frames + hold_frames + orbit_frames

    # ── PHASE 1: REVEAL
    for i in range(reveal_frames):
        raw   = i / (reveal_frames - 1)
        eased = _ease_quintic(raw)
        tc    = max(2, int(eased * N_t))
        # Camera rises from flat (elev=8) to full view (elev=26)
        elev  = 8.0 + 18.0 * raw
        azim  = -55.0 + 8.0 * raw
        alpha = 0.4 + 0.6 * raw
        schedule.append(dict(
            phase="REVEAL  (t = {}/{})".format(tc, N_t),
            t_cutoff=tc, azim=azim, elev=elev, alpha=alpha,
            global_progress=i / (total - 1),
        ))

    # ── PHASE 2: HOLD
    for i in range(hold_frames):
        frac = i / max(hold_frames - 1, 1)
        azim = -47.0 + 4.0 * np.sin(np.pi * frac)
        elev = 26.0 + 2.0 * np.sin(np.pi * frac * 2)
        schedule.append(dict(
            phase="FULL SURFACE",
            t_cutoff=N_t, azim=azim, elev=elev, alpha=1.0,
            global_progress=(reveal_frames + i) / (total - 1),
        ))

    # ── PHASE 3: ORBIT
    for i in range(orbit_frames):
        frac = i / max(orbit_frames - 1, 1)
        azim = -47.0 + 360.0 * frac
        elev = 26.0 + 14.0 * np.sin(np.pi * frac)
        schedule.append(dict(
            phase="ORBITING  {:.0f}°".format(azim % 360),
            t_cutoff=N_t, azim=azim, elev=elev, alpha=1.0,
            global_progress=(reveal_frames + hold_frames + i) / (total - 1),
        ))

    return schedule


# ═══════════════════════════════════════════════════════════════════════
# MASTER RENDER
# ═══════════════════════════════════════════════════════════════════════

def render_animation(data_bundle, engine_bundle, mesh,
                     out_path=CONFIG["ANIM_GIF"],
                     reveal_frames=30,
                     hold_frames=15,
                     orbit_frames=55):
    """
    Render the smooth thermodynamic animation GIF.
    Default: 30+15+55 = 100 frames @ 10 fps = 10s loop.
    """
    N_t      = mesh["N_t"]
    schedule = _build_schedule(N_t, reveal_frames, hold_frames, orbit_frames)
    total    = len(schedule)
    log(f"Animation schedule: {total} frames  "
        f"(reveal={reveal_frames}, hold={hold_frames}, orbit={orbit_frames})")

    frames = []

    for fi, entry in enumerate(schedule):
        if fi % 5 == 0:
            log(f"  Frame {fi+1:3d}/{total}  "
                f"[{entry['phase']}  "
                f"azim={entry['azim']:.1f}  elev={entry['elev']:.1f}]")

        frame = _render_frame(
            engine_bundle  = engine_bundle,
            data_bundle    = data_bundle,
            mesh           = mesh,
            azim           = entry["azim"],
            elev           = entry["elev"],
            t_cutoff       = entry["t_cutoff"],
            phase_label    = entry["phase"],
            global_progress= entry["global_progress"],
            reveal_alpha   = entry["alpha"],
        )
        frames.append(frame)

    log(f"Writing GIF  [{total} frames @ {CONFIG['GIF_FPS']} fps] ...")
    imageio.mimsave(
        out_path, frames, format="GIF",
        duration=1.0 / CONFIG["GIF_FPS"], loop=0,
    )
    mb = os.path.getsize(out_path) / 1e6
    log(f"GIF saved -> {out_path}  ({mb:.1f} MB, {total} frames)")
