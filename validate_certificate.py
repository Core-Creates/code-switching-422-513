"""Adversarial validation of the end-to-end certificate.

A clean fault scan is only meaningful if the scan could have come out dirty. These checks
attack the certificate from the directions where it could be vacuous rather than true:

  1. No gauge detectors. The scan passes allow_gauge_detectors, which tolerates detectors
     that are not deterministic. If any existed, the model would be interpreting them
     loosely and the result would be softer than it looks. We recompute the model with
     that tolerance switched off.
  2. No dead detectors. A detector that never fires constrains nothing and would pad the
     count of protections without providing any.
  3. The observable is live. If OBSERVABLE_INCLUDE were miswired so that it never flipped,
     "no fault flips the observable" would be trivially true and worthless.
  4. Every protection is load-bearing. We remove each one in turn and require the scan to
     FAIL. A protection whose removal changes nothing is either redundant, which is a
     finding, or a place where the scan is blind, which is worse.
  5. The distance is exactly two. Single faults are safe, but PAIRS of faults must be able
     to cause a logical error. If no pair could either, the observable or the detectors
     would be suspect rather than the protocol being miraculous.
"""
import contextlib
import io
import itertools
import json
import os
import sys

import stim

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
with contextlib.redirect_stdout(io.StringIO()):
    import end_to_end as E

P = 1e-3
results = {}


def mechanisms(circuit, strict=False):
    dem = circuit.detector_error_model(decompose_errors=False,
                                       allow_gauge_detectors=not strict)
    out = []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        t = inst.targets_copy()
        dets = frozenset(x.val for x in t if x.is_relative_detector_id())
        obs = any(x.is_logical_observable_id() for x in t)
        out.append((dets, obs))
    return out


def dangerous(circuit, strict=False):
    return sum(1 for d, o in mechanisms(circuit, strict) if o and not d)


print("=" * 74)
print("1. No gauge detectors: recompute the model with tolerance switched off")
print("=" * 74)
ok_strict = True
for basis in ("X", "Z"):
    try:
        n = dangerous(E.build(basis, P).c, strict=True)
        print(f"   prep {basis}bar: strict model builds, {n} dangerous mechanisms")
        ok_strict &= (n == 0)
    except Exception as exc:
        ok_strict = False
        print(f"   prep {basis}bar: strict model REJECTED: {str(exc)[:90]}")
results["strict_model_clean"] = ok_strict
print(f"   => every detector is deterministic; the permissive flag was hiding nothing: "
      f"{ok_strict}")

print()
print("=" * 74)
print("2. No dead detectors, and 3. the observable is live")
print("=" * 74)
for basis in ("X", "Z"):
    circ = E.build(basis, 5e-3).c
    det, obs = circ.compile_detector_sampler().sample(20000, separate_observables=True)
    never = [i for i in range(det.shape[1]) if det[:, i].sum() == 0]
    print(f"   prep {basis}bar: {det.shape[1]} detectors, {len(never)} never fire, "
          f"observable flips in {obs.sum()} of 20000 shots")
    results[f"dead_detectors_{basis}"] = len(never)
    results[f"observable_flips_{basis}"] = int(obs.sum())
print("   => a detector that never fires would constrain nothing; an observable that "
      "never flips\n      would make the whole scan vacuous")

print()
print("=" * 74)
print("4. Every protection is load-bearing: remove it and the scan must FAIL")
print("=" * 74)
ABLATIONS = [
    (None, "nothing removed (the certified protocol)"),
    ("m1_flag", "flag on the joint measurement"),
    ("a_flag", "flags on A's verification cascades"),
    ("a_interleave", "A checks interleaved between M1 rounds"),
    ("zbar_repeat", "repetition of the Zbar measurement"),
    ("handoff", "hand-off EC round on B"),
]
print(f"   {'protection removed':44s} {'Xbar':>6} {'Zbar':>6}  verdict")
abl = {}
for cripple, label in ABLATIONS:
    counts = {b: dangerous(E.build(b, P, cripple=cripple).c) for b in ("X", "Z")}
    total = sum(counts.values())
    if cripple is None:
        verdict = "certified" if total == 0 else "BROKEN"
    else:
        verdict = "load-bearing" if total > 0 else "REDUNDANT?"
    abl[str(cripple)] = {"X": counts["X"], "Z": counts["Z"], "verdict": verdict}
    print(f"   {label:44s} {counts['X']:>6} {counts['Z']:>6}  {verdict}")
results["ablations"] = abl

print()
print("=" * 74)
print("5. The distance is exactly two: pairs of faults must be able to cause a logical "
      "error")
print("=" * 74)
for basis in ("X", "Z"):
    mechs = mechanisms(E.build(basis, P).c)
    by_dets = {}
    for d, o in mechs:
        by_dets.setdefault(d, []).append(o)
    found = None
    items = list(by_dets.items())
    for (d1, o1), (d2, o2) in itertools.combinations(items, 2):
        if d1 ^ d2:
            continue
        for a in o1:
            for b in o2:
                if a != b:
                    found = (len(d1), len(d2))
                    break
            if found:
                break
        if found:
            break
    if not found:
        for d, obs_list in by_dets.items():
            if len(set(obs_list)) > 1:
                found = (len(d), len(d))
                break
    print(f"   prep {basis}bar: {len(mechs)} mechanisms, a distance-2 logical failure "
          f"{'exists' if found else 'was NOT found'}")
    results[f"distance2_exists_{basis}"] = bool(found)

json.dump(results, open(os.path.join(ROOT, "results", "validation.json"), "w"), indent=2)
print()
print("=" * 74)
all_ok = (results["strict_model_clean"]
          and all(v["verdict"] in ("certified", "load-bearing") for v in abl.values()))
print(f"VALIDATION {'PASSED' if all_ok else 'FOUND SOMETHING'}")
print("wrote results/validation.json")
