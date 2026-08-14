"""Step 2, outer loop: the flag placement failed for our first encoder, so resynthesize
the cascade and rerun. The frame map has freedom -- which input stabilizer is sent to
which [[5,1,3]] generator is a choice (4! = 24 bijections), and Stim offers two
tableau-to-circuit methods. Each choice yields a different cascade with different
error-spreading structure. We sweep them all and rerun the whole flag search on each.
"""
import itertools
import json

import stim

import frames as F
import flagsearch as FS
from frames import ps

import os
DONE = set()
if os.path.exists("sweep_rows.jsonl"):
    for line in open("sweep_rows.jsonl"):
        DONE.add(tuple(json.loads(line)["perm"]))
rows = [json.loads(l) for l in open("sweep_rows.jsonl")] if os.path.exists("sweep_rows.jsonl") else []
for perm in itertools.permutations(range(4)):
    if perm in DONE:
        continue
    out_stab = [F.OUT_STAB[i] for i in perm]
    T_in = F.frame_tableau(F.IN_STAB, F.IN_X, F.IN_Z)
    T_out = F.frame_tableau(out_stab, F.OUT_X, F.OUT_Z)
    U = T_in.inverse().then(T_out)
    pairs = list(zip(F.IN_STAB, out_stab)) + [(F.IN_X, F.OUT_X), (F.IN_Z, F.OUT_Z)]
    for method in ("elimination",):
        circ = U.to_circuit(method=method)
        T = stim.Tableau.from_circuit(circ)
        assert all(T(ps(a)) == ps(b) for a, b in pairs), "resynthesized U is wrong"
        enc = FS.Encoder(circ, pairs)
        base_bad, _, base_n, _, _ = FS.evaluate(enc.faults((), False), False)
        nvalid, bestA, bestB = FS.single_flag_search(enc, strict_only=True)
        rows.append({"perm": list(perm), "method": method, "cx": enc.ncx,
                     "gates": enc.n, "baseline_bad": base_bad, "locations": base_n,
                     "valid_flags": nvalid,
                     "best_strict": bestA[0] if bestA else None,
                     "best_strict_design": str(bestA[1]) if bestA else None,
                     "best_postsel": bestB[0] if bestB else -1,
                     "best_postsel_design": str(bestB[1]) if bestB else None})
        with open("sweep_rows.jsonl", "a") as fh:
            fh.write(json.dumps(rows[-1]) + chr(10))
        r = rows[-1]
        print(f"perm {perm} {method:12s} CX={enc.ncx:3d} baseline_bad={base_bad:2d} "
              f"valid_flags={nvalid:4d} best_strict={r['best_strict']:2d} "
              f"best_postsel=n/a", flush=True)

json.dump(rows, open("step2_encoder_sweep.json", "w"), indent=2)
print()
best = min(rows, key=lambda r: (r['best_strict'], r['cx']))
print("BEST STRICT over all resynthesized cascades:")
print(f"   perm={best['perm']} method={best['method']} CX={best['cx']} "
      f"bad buckets={best['best_strict']} design={best['best_strict_design']}")

print(f"\nsmallest cascade found: {min(r['cx'] for r in rows)} CX "
      f"(largest {max(r['cx'] for r in rows)})")
