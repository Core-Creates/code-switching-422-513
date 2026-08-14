"""Step 3: widen the flag family.

Step 2 closed the family of one or two BRACKETING-PAIR flags: 97,466 valid designs
across all 24 cascades, none certifying. This widens the family to flags with three and
four couplings, and to couplings that touch different data qubits, which the pair family
could not express.

Tractability comes from an algebraic prefilter (flagsearch.coupling_keys): the data part
of the measured flag operator's image is the XOR of per-coupling keys, so a necessary
condition for the flag to be deterministic is that those keys cancel. That is two integer
XORs per coupling with no tableau, and it removes 1.87 million of the 1.87 million size-3
candidates down to a few thousand. Sufficiency is still decided by Encoder.valid().

Subsets containing a smaller cancelling subset are skipped as non-primitive: they are a
smaller flag with redundant couplings bolted on, not a new gadget.
"""
import json
import sys
import time

import stim

import flagsearch as FS

CAP4 = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
enc = FS.Encoder(stim.Circuit.from_file("encoder.stim"))
print(f"cascade: {enc.n} gate locations, {enc.ncx} two-qubit gates")
print(f"size-4 search is capped at {CAP4} candidates per kind; sizes 2 and 3 are "
      f"exhaustive\n")

t0 = time.time()
stats, results = FS.wide_search(enc, sizes=(2, 3, 4), cap=CAP4, primitive=True)
print(f"\nsearched in {time.time() - t0:.0f}s")

n_valid = sum(v for _, v in stats.values())
n_cand = sum(c for c, _ in stats.values())
certifying = [r for r in results if r[0] == 0]
print(f"total: {n_cand} prefiltered candidates, {n_valid} valid flags, "
      f"{len(certifying)} certifying")
print(f"best bad-bucket count: {results[0][0] if results else 'n/a'}")

by_size = {}
for bad, design, nfl, ntot in results:
    k = len(design[0][1])
    if k not in by_size or bad < by_size[k][0]:
        by_size[k] = (bad, design, nfl, ntot)
print("\nbest design per coupling count:")
for k in sorted(by_size):
    bad, design, nfl, ntot = by_size[k]
    kind, coups = design[0]
    print(f"  {k} couplings, kind {kind}: bad={bad}, flags {nfl}/{ntot} locations, "
          f"couplings (slot,qubit)={list(coups)}")

summary = {"cap_size4_per_kind": CAP4, "candidates": n_cand, "valid": n_valid,
           "certifying": len(certifying),
           "best_bad": results[0][0] if results else None,
           "per_group": {f"{k[0]}{k[1]}": v for k, v in stats.items()},
           "best_per_size": {str(k): [v[0], str(v[1])] for k, v in by_size.items()}}
json.dump(summary, open("results/step3_wide_summary.json", "w"), indent=2)

if certifying:
    bad, design, nfl, ntot = certifying[0]
    print(f"\nCERTIFYING DESIGN: {design}")
    _, _, _, buckets, _ = FS.evaluate(enc.faults(design), False)
    lines = []
    for key in sorted(buckets):
        e = FS.canon(buckets[key][0][1])
        best = min(((e[0] ^ sx, e[1] ^ sz) for sx, sz in FS.STAB16),
                   key=lambda c: sum(1 for i in range(5)
                                     if (c[0] >> i & 1) or (c[1] >> i & 1)))
        lines.append(f"syndrome {key[0]} flag {key[1]} -> {FS.pauli_str(best)} "
                     f"({len(buckets[key])} fault locations)")
    print("\nSYNTHESIZED DECODER")
    for line in lines:
        print("   " + line)
    open("results/decoder_certificate.txt", "w").write("\n".join(lines) + "\n")
else:
    print("\nNo design in the widened single-flag family certifies Phase 3.")
