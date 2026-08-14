"""Figures for the manuscript, generated from the circuits and result files.

No figure is drawn by hand. Figure 1 is rendered from the same stim circuit the fault
analysis enumerates; Figure 2 is plotted from results/numerics.json.
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "paper", "figures")
os.makedirs(OUT, exist_ok=True)

import stim  # noqa: E402
import frames as F  # noqa: E402
import teleport_fault_analysis as T  # noqa: E402


def fig_joint_measurement():
    """The flag-protected joint logical measurement, rendered from the circuit."""
    gates = T.build(T.DEFAULT_ORDER, (0, 7))
    c = stim.Circuit()
    c.append("I", range(T.NQ))
    for name, tg in gates:
        c.append(name, tg)
    text = str(c.diagram("timeline-text"))
    lines = text.split("\n")
    fig, ax = plt.subplots(figsize=(11, 0.28 * len(lines) + 0.8))
    ax.axis("off")
    ax.text(0.0, 1.0, text, family="monospace", fontsize=7.5, va="top", ha="left")
    fig.tight_layout()
    path = os.path.join(OUT, "fig1_joint_measurement.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path, len(lines)


def fig_numerics():
    with open(os.path.join(ROOT, "results", "numerics.json")) as fh:
        data = json.load(fh)
    cert = data["certified"]
    crip = data["M1 flag removed"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    ps = [r["p"] for r in cert["rows"]]
    acc = [r["acceptance"] for r in cert["rows"]]
    ax1.plot(ps, acc, "o-", color="#2b6cb0")
    ax1.set_xscale("log")
    ax1.set_xlabel("physical error rate p")
    ax1.set_ylabel("acceptance rate")
    ax1.set_title("Post-selection yield")
    ax1.grid(alpha=0.3)
    ax1.set_ylim(0, 1)

    for rows, label, style, colour in ((cert["rows"], "certified", "o-", "#2b6cb0"),
                                       (crip["rows"], "M1 flag removed", "s--", "#c05621")):
        xs = [r["p"] for r in rows if r["errors"]]
        ys = [r["p_logical"] for r in rows if r["errors"]]
        ax2.plot(xs, ys, style, color=colour, label=label)
    lo, hi = min(ps), max(ps)
    ax2.plot([lo, hi], [lo, hi], ":", color="grey", label="p_L = p")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("physical error rate p")
    ax2.set_ylabel("logical error rate p_L")
    ax2.set_title(f"slopes {cert['slope']:.2f} and {crip['slope']:.2f}")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    path = os.path.join(OUT, "fig2_numerics.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path, cert["slope"], crip["slope"]


if __name__ == "__main__":
    p1, n = fig_joint_measurement()
    print(f"wrote {p1} ({n} rendered lines)")
    p2, s1, s2 = fig_numerics()
    print(f"wrote {p2} (slopes {s1:.2f}, {s2:.2f})")
