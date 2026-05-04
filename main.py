"""
╔══════════════════════════════════════════════════════════════════════╗
║   THERMODYNAMIC ARROW OF TIME  |  S&P 500 MARKET ENTROPY ENGINE    ║
║   main.py  —  MASTER PIPELINE ORCHESTRATOR                           ║
║                                                                      ║
║  Run:   python main.py                                               ║
║                                                                      ║
║  Outputs                                                             ║
║  ───────                                                             ║
║  outputs/thermo_arrow_of_time.png  — 1920×1080 static image         ║
║  outputs/thermo_animation.gif      — 100-frame smooth animated GIF  ║
║                                                                      ║
║  Pipeline                                                            ║
║  ────────                                                            ║
║  MODULE 1  data.py    → calibrated synthetic S&P 500 returns        ║
║  MODULE 2  engine.py  → rolling KL entropy production surface       ║
║  MODULE 3  visual.py  → static 1920×1080 PNG                        ║
║  MODULE 4  animate.py → 100-frame GIF (reveal → hold → orbit)       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import time
from datetime import datetime
from config  import CONFIG
from data    import fetch_all
from engine  import compute_entropy_surface, build_surface_mesh
from visual  import render_static
from animate import render_animation


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  MAIN  |  {msg}")


def banner(text):
    line = "═" * 68
    print(f"\n{line}\n  {text}\n{line}\n")


def main():
    t0 = time.time()

    banner("MODULE 1  ──  DATA  (calibrated GBM | 30 S&P 500 stocks | 2Y)")
    data_bundle = fetch_all()

    banner("MODULE 2  ──  ENGINE  (rolling KL entropy production surface)")
    engine_bundle = compute_entropy_surface(data_bundle)
    mesh          = build_surface_mesh(engine_bundle)

    banner("MODULE 3  ──  VISUAL  (static 1920×1080 PNG)")
    render_static(data_bundle, engine_bundle, mesh,
                  out_path=CONFIG["STATIC_PNG"])

    banner("MODULE 4  ──  ANIMATION  (100-frame smooth GIF)")
    render_animation(data_bundle, engine_bundle, mesh,
                     out_path=CONFIG["ANIM_GIF"],
                     reveal_frames=30,
                     hold_frames=15,
                     orbit_frames=55)

    elapsed = time.time() - t0
    banner(f"DONE  ──  total time = {elapsed/60:.1f} min")
    log(f"Static  ->  {CONFIG['STATIC_PNG']}")
    log(f"GIF     ->  {CONFIG['ANIM_GIF']}")


if __name__ == "__main__":
    main()
