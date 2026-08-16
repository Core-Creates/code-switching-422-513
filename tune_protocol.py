"""Two questions the certificate cannot answer on its own.

1. Are the repetition counts justified? r = 3 for the M1 and Zbar measurements was chosen
   by convention, not by evidence, which is exactly the kind of number that gets picked
   once and never revisited. We ablate it the same way we ablated the protections: does
   the certificate survive at r = 2, and what does that cost or save?

2. Where does the yield actually go? Acceptance is reported as one number, but
   post-selection happens at several independent stages. Knowing which stage discards most
   is what tells you where yield work would pay, and it is the first thing a referee will
   ask about a factory protocol.
"""
import contextlib
import io
import itertools
import json
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
with contextlib.redirect_stdout(io.StringIO()):
    import end_to_end as E

SHOTS = int(sys.argv[1]) if len(sys.argv) > 1 else 400_000
P = 5e-3
out = {}


def two_qubit_gates(**kw):
    return sum(len(i.targets_copy()) // 2
               for i in E.build("Z", 0.0, **kw).c.flattened()
               if i.name in ("CX", "CY", "CZ"))


def yield_and_error(m1, zb, p=P, shots=SHOTS):
    """Acceptance AND logical error rate. Measuring only acceptance is how you end up
    recommending a configuration that is cheaper, higher yielding, and worse: the first
    version of this script did exactly that."""
    tot = acc = err = 0
    for basis in ("X", "Z"):
        circ = E.build(basis, p, m1_rounds=m1, zbar_rounds=zb).c
        det, obs = circ.compile_detector_sampler().sample(shots // 2,
                                                          separate_observables=True)
        keep = ~det.any(axis=1)
        acc += int(keep.sum())
        err += int(obs[keep].sum())
        tot += shots // 2
    return acc / tot, (err / acc if acc else float("nan")), err


print("=" * 76)
print("1. Repetition counts: is r = 3 earning its place?")
print("=" * 76)
print(f"   {'M1 rounds':>9} {'Zbar rounds':>12} {'2q gates':>9} {'dangerous':>10} "
      f"{'acceptance':>11} {'p_L':>11} {'errors':>7}")
rows = []
for m1, zb in itertools.product((1, 2, 3), (1, 2, 3)):
    danger = sum(E.scan(E.build(b, 1e-3, m1_rounds=m1, zbar_rounds=zb).c)
                 for b in ("X", "Z"))
    n2 = two_qubit_gates(m1_rounds=m1, zbar_rounds=zb)
    acc, pl, ne = yield_and_error(m1, zb) if danger == 0 else (float("nan"),) * 2 + (0,)
    rows.append({"m1_rounds": m1, "zbar_rounds": zb, "two_qubit_gates": n2,
                 "dangerous": danger, "acceptance": None if danger else acc,
                 "p_logical": None if danger else pl, "errors": ne})
    tag = "" if danger else f"{acc:11.4f} {pl:11.3e} {ne:>7}"
    print(f"   {m1:>9} {zb:>12} {n2:>9} {danger:>10} {tag}"
          + ("   <- fails" if danger else ""))
out["rounds"] = rows

viable = [r for r in rows if r["dangerous"] == 0]
cheapest = min(viable, key=lambda r: r["two_qubit_gates"])
lowest = min(viable, key=lambda r: r["p_logical"])
print(f"\n   cheapest certifying:  M1 r={cheapest['m1_rounds']} Zbar "
      f"r={cheapest['zbar_rounds']}, {cheapest['two_qubit_gates']} gates, acceptance "
      f"{cheapest['acceptance']:.4f}, p_L {cheapest['p_logical']:.3e}")
print(f"   lowest logical error: M1 r={lowest['m1_rounds']} Zbar "
      f"r={lowest['zbar_rounds']}, {lowest['two_qubit_gates']} gates, acceptance "
      f"{lowest['acceptance']:.4f}, p_L {lowest['p_logical']:.3e}")
print("\n   These are different configurations, and that is the whole point. Fewer M1")
print("   rounds buy gates and yield and pay for them in logical error rate. For a")
print("   factory whose product is a low-error encoded state, p_L is the objective and")
print("   yield is the budget, so the protocol keeps r = 3.")
print("   Zbar r=2 against r=3 is within Poisson noise on these counts, so the extra")
print("   round is not justified by this data and not ruled out by it either. It stays")
print("   at 3 because changing it on a null result would be churn.")
out["cheapest"] = cheapest
out["lowest_error"] = lowest

print()
print("=" * 76)
print(f"2. Where the yield goes, at p = {P}")
print("=" * 76)
b = E.build("Z", P)
labels = b.det_labels
det, _ = b.c.compile_detector_sampler().sample(SHOTS, separate_observables=True)
by_stage = defaultdict(list)
for i, lab in enumerate(labels):
    by_stage[lab].append(i)

overall = float((~det.any(axis=1)).mean())
print(f"   overall acceptance {overall:.4f}\n")
print(f"   {'stage':16s} {'detectors':>9} {'fires':>8} {'if only':>9} {'if all but':>11}")
stages = []
for stage, idx in sorted(by_stage.items(), key=lambda kv: -len(kv[1])):
    fires = float((det[:, idx].any(axis=1)).mean())
    others = [i for i in range(len(labels)) if i not in idx]
    without = float((~det[:, others].any(axis=1)).mean())
    stages.append({"stage": stage, "detectors": len(idx), "fire_rate": fires,
                   "acceptance_if_only_this": 1 - fires,
                   "acceptance_without_this": without})
    print(f"   {stage:16s} {len(idx):>9} {fires:>8.4f} {1 - fires:>9.4f} {without:>11.4f}")
out["stages"] = stages
worst = max(stages, key=lambda s: s["fire_rate"])
print(f"\n   {worst['stage']} discards most: it alone would cap acceptance at "
      f"{1 - worst['fire_rate']:.4f}")
print("   'if only' is acceptance with just that stage's checks; 'if all but' is "
      "acceptance\n   with that stage removed. Neither is a proposal, both say where "
      "the yield goes.")

json.dump(out, open(os.path.join(ROOT, "results", "tuning.json"), "w"), indent=2)
print("\nwrote results/tuning.json")
