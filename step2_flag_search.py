"""Step 2: the flag placement and the decoder are OUTPUTS of the fault analysis.

For every candidate flag design we
  (1) check the design is a valid flag at all: in the fault-free run the flag readout
      must be deterministic and the encoder's frame map must be unchanged,
  (2) run the complete single-fault enumeration,
  (3) bucket faults by (syndrome, flag) and try to SYNTHESIZE a decoder: one
      correction per bucket that works for every fault in it, up to stabilizers.
Designs whose buckets mix logically inequivalent residuals are rejected.

FAULT MODEL (stated explicitly, as it must be in the paper):
  gate locations : every gate of arity k contributes all 4^k - 1 non-identity Paulis
                   on its support, applied immediately after the gate. Correlated
                   multi-qubit faults are therefore included for any k, not just k=2.
  preparation    : X on the fresh q5 (|0>); on each flag ancilla, the non-trivial
                   Pauli for its basis
  measurement    : a classical flip of each flag readout
  idle           : optionally, X,Y,Z on every qubit at every circuit slot
Faults acting trivially on a fresh ancilla (Z on |0>, X on |+>) are excluded: they are
not physical faults.

OUT OF SCOPE, by Lemma 1 (see FINDINGS.md): errors already present on the data block
when Phase 3 begins. Those are provably uncorrectable by any encoder and any decoder,
so they are Phase 0's post-selection problem, not Phase 3's.

ASSUMPTION: Phase 4 syndrome extraction is ideal here; it is Chao-Reichardt's gadget
for [[5,1,3]] and carries its own separate certificate.
"""
import itertools
import json
import time

import stim

import flagsearch as FS

ENC = FS.Encoder(stim.Circuit.from_file("encoder.stim"))
report = {"encoder_two_qubit_gates": ENC.ncx, "gate_locations": ENC.n,
          "arity_histogram": ENC.arity_histogram}
print(f"encoder: {ENC.n} gate locations, arity histogram {ENC.arity_histogram}, "
      f"{ENC.ncx} two-qubit gates")
print("fault model: " + ENC.fault_model_summary())

# =============================================================== baseline
for include_idle in (False, True):
    tag = "gate+idle" if include_idle else "gate-only"
    faults = ENC.faults((), include_idle)
    bad, nfl, ntot, buckets, badkeys = FS.evaluate(faults, False)
    print(f"\nBASELINE no flag [{tag}]: {ntot} fault locations, {len(buckets)} buckets, "
          f"{bad} undecodable -> {'FT' if bad == 0 else 'NOT FT'}")
    report[f"baseline_{tag}"] = {"locations": ntot, "bad_buckets": bad}
    if not include_idle:
        for key in badkeys[:3]:
            reps = {}
            for lab, e in buckets[key]:
                reps.setdefault(FS.canon(e), lab)
            base = next(iter(reps))
            parts = [f"{lab}" + ("" if e == base else
                     f" [differs by logical {FS.logical_class((e[0]^base[0], e[1]^base[1]))}]")
                     for e, lab in list(reps.items())[:3]]
            print(f"   syndrome {key[0]}: " + "  vs  ".join(parts))

# =============================================================== single flags
print("\nSearching single-flag designs...")
t0 = time.time()
res = {"strict": [], "postsel": []}
nvalid = 0
for kind in ("X", "Z"):
    for d in range(5):
        for t1 in range(ENC.n + 1):
            for t2 in range(t1 + 1, ENC.n + 1):
                design = ((kind, d, t1, t2),)
                f = ENC.faults(design)
                if f is None:
                    continue
                nvalid += 1
                badA, nfl, ntot, _, _ = FS.evaluate(f, False)
                badB, _, _, _, _ = FS.evaluate(f, True)
                res["strict"].append((badA, design, nfl, ntot))
                res["postsel"].append((badB, design, nfl, ntot))
print(f"   {nvalid} of {2 * 5 * (ENC.n + 1) * ENC.n // 2} candidates are VALID flags "
      f"(pair cancels, frame map preserved)   [{time.time()-t0:.1f}s]")
for crit in ("strict", "postsel"):
    rows = sorted(res[crit])
    n_ok = sum(1 for r in rows if r[0] == 0)
    print(f"   {crit:8s}: {n_ok} fully decodable; best bad-bucket count = {rows[0][0]}")
    for bad, design, nfl, ntot in rows[:3]:
        print(f"      {design}  bad={bad}  flags {nfl}/{ntot} locations")
report["valid_single_flags"] = nvalid
report["single_flag_strict_ok"] = sum(1 for r in res["strict"] if r[0] == 0)
report["single_flag_postsel_ok"] = sum(1 for r in res["postsel"] if r[0] == 0)

# =============================================================== two flags
best_singles = [d for _, d, _, _ in sorted(res["strict"])[:30]]
print(f"\nSearching two-flag designs over the {len(best_singles)} best singles "
      f"({len(best_singles)*(len(best_singles)-1)//2} pairs)...")
t0 = time.time()
two = {"strict": [], "postsel": []}
for a, b in itertools.combinations(best_singles, 2):
    design = (a[0], b[0])
    f = ENC.faults(design)
    if f is None:
        continue
    badA, nfl, ntot, _, _ = FS.evaluate(f, False)
    badB, _, _, _, _ = FS.evaluate(f, True)
    two["strict"].append((badA, design, nfl, ntot))
    two["postsel"].append((badB, design, nfl, ntot))
for crit in ("strict", "postsel"):
    rows = sorted(two[crit])
    n_ok = sum(1 for r in rows if r[0] == 0)
    print(f"   {crit:8s}: {n_ok} of {len(rows)} valid pairs fully decodable; "
          f"best = {rows[0][0] if rows else 'n/a'}")
    for bad, design, nfl, ntot in rows[:2]:
        print(f"      {design}  bad={bad}  flags {nfl}/{ntot} locations")
print(f"   [{time.time()-t0:.1f}s]")
report["two_flag_strict_ok"] = sum(1 for r in two["strict"] if r[0] == 0)
report["two_flag_postsel_ok"] = sum(1 for r in two["postsel"] if r[0] == 0)
print(f"   NOTE: the two-flag stage searches only pairs drawn from the 30 best single "
      f"designs, not all {len(res['strict'])*(len(res['strict'])-1)//2} pairs.")

# =========================================== winner + synthesized decoder table
winner = None
for pool, crit in ((two, "strict"), (res, "strict"), (two, "postsel"), (res, "postsel")):
    rows = sorted(pool[crit])
    if rows and rows[0][0] == 0:
        winner = (rows[0][1], crit)
        break
report["winner"] = str(winner)
json.dump(report, open("step2_summary.json", "w"), indent=2)

if winner is None:
    print("\nNO design in the searched space certifies Phase 3. "
          "The cascade itself must be resynthesized (see FINDINGS.md).")
else:
    design, crit = winner
    print(f"\nWINNER ({crit}): {design}")
    _, _, _, buckets, _ = FS.evaluate(ENC.faults(design), crit == "postsel")
    lines = []
    for key in sorted(buckets):
        e = FS.canon(buckets[key][0][1])
        best = min(((e[0] ^ sx, e[1] ^ sz) for sx, sz in FS.STAB16),
                   key=lambda c: sum(1 for i in range(5)
                                     if (c[0] >> i & 1) or (c[1] >> i & 1)))
        lines.append(f"syndrome {key[0]} flag {key[1]} -> {FS.pauli_str(best)} "
                     f"({len(buckets[key])} fault locations)")
    print("\nSYNTHESIZED DECODER")
    for l in lines:
        print("   " + l)
    open("decoder_certificate.txt", "w").write("\n".join(lines) + "\n")
