"""Step 8: Monte Carlo under circuit-level depolarizing noise.

Two curves, both taken from the same end-to-end circuit that carries the certificate:

  acceptance rate     fraction of shots in which no detector fires. Post-selection is
                      load-bearing at four separate stages (A's input verification, B's
                      preparation verification, every flag, and the ZZZZ readout check),
                      so this is the number that decides whether the factory yields.
  logical error rate  fraction of ACCEPTED shots in which the teleported observable is
                      wrong.

The slope of log p_L against log p is an independent check on the end-to-end enumeration.
That enumeration says no single fault produces an undetectable logical error, so the
leading term must be quadratic and the fitted slope must come out near 2. The crippled
variant, with the M1 flag removed, has a single-fault mechanism and must come out near 1.
A combinatorial proof and a numerical exponent agreeing is worth more than either alone.
"""
import json
import math
import sys

import numpy as np

import end_to_end as E

SHOTS = int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000
PS = [1e-3, 2e-3, 3e-3, 5e-3, 7e-3, 1e-2]


def run(basis, p, shots, cripple=None):
    circ = E.build(basis, p, cripple=cripple).c
    det, obs = circ.compile_detector_sampler().sample(shots, separate_observables=True)
    accepted = ~det.any(axis=1)
    n_acc = int(accepted.sum())
    n_err = int(obs[accepted].sum())
    return n_acc, n_err


def fit_slope(xs, ys):
    """least squares slope of log y against log x, over points with y > 0"""
    pts = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if y > 0]
    if len(pts) < 2:
        return float("nan")
    n = len(pts)
    sx = sum(a for a, _ in pts)
    sy = sum(b for _, b in pts)
    sxx = sum(a * a for a, _ in pts)
    sxy = sum(a * b for a, b in pts)
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


print(f"Circuit-level depolarizing noise, {SHOTS:,} shots per point\n")
results = {}
for label, cripple in (("certified", None), ("M1 flag removed", "m1_flag")):
    print(f"=== {label} ===")
    print(f"{'p':>8} {'acceptance':>12} {'accepted':>12} {'logical errors':>15} {'p_L':>12}")
    ps_used, pls = [], []
    rows = []
    for p in PS:
        acc_tot = err_tot = 0
        for basis in ("X", "Z"):
            a, e = run(basis, p, SHOTS // 2, cripple)
            acc_tot += a
            err_tot += e
        acc_rate = acc_tot / SHOTS
        pl = err_tot / acc_tot if acc_tot else float("nan")
        rows.append({"p": p, "acceptance": acc_rate, "accepted": acc_tot,
                     "errors": err_tot, "p_logical": pl})
        print(f"{p:8.4f} {acc_rate:12.4f} {acc_tot:12,} {err_tot:15,} {pl:12.3e}")
        if err_tot:
            ps_used.append(p)
            pls.append(pl)
    slope = fit_slope(ps_used, pls)
    print(f"   fitted slope of log p_L vs log p: {slope:.2f}")
    results[label] = {"rows": rows, "slope": slope}
    print()

cert_slope = results["certified"]["slope"]
crip_slope = results["M1 flag removed"]["slope"]
print("=" * 70)
print(f"certified protocol slope {cert_slope:.2f}, expected near 2 because the "
      f"enumeration found\n   no single-fault logical error")
print(f"crippled protocol slope  {crip_slope:.2f}, expected near 1 because removing the "
      f"M1 flag\n   reintroduces one")

# pseudothreshold: where p_L crosses p
rows = results["certified"]["rows"]
cross = None
for a, b in zip(rows, rows[1:]):
    if a["p_logical"] < a["p"] and b["p_logical"] >= b["p"]:
        cross = (a["p"], b["p"])
if cross:
    print(f"\npseudothreshold (p_L = p) lies between {cross[0]:.4f} and {cross[1]:.4f}")
else:
    below = all(r["p_logical"] < r["p"] for r in rows if not math.isnan(r["p_logical"]))
    print(f"\np_L stays {'below' if below else 'above'} p across the sampled range "
          f"{PS[0]} to {PS[-1]}; the pseudothreshold is outside it")

json.dump(results, open("results/numerics.json", "w"), indent=2)
print("\nwrote results/numerics.json")
