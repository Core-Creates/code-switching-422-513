"""Step 4: two flag bits, which is the minimum the counting bound allows.

Bound (placement-independent, see step3 output and FINDINGS.md): partition the Phase 3
single-fault locations by [[5,1,3]] syndrome. Every one of the 16 classes contains 3 or 4
logically inequivalent residuals. A decoder keyed on (syndrome, flag) can only split each
class into 2^b groups, so b >= ceil(log2 4) = 2 flag bits are necessary no matter where
the couplings go. That is why every single-flag search failed, and it means a certificate
can only live in the two-flag family.

Method. For a flag of kind X the readout flips iff the propagated fault has an X
component on the coupled data qubit at the coupling slot (CX(d->f) sends X_d -> X_d X_f);
for kind Z it is the Z component. So we precompute, per fault, the whole trace of X and Z
components over every (slot, qubit) site, as one integer each. A flag is then just a mask
over sites, and its bit on a fault is the parity of trace AND mask. That makes evaluating
a candidate flag O(1) per fault with no tableau at all.

Two flags certify iff, within every syndrome class, no two faults with logically
inequivalent residuals share a (bit1, bit2) label. We turn that into a set-cover: each
constraint is a pair of faults that must be separated, each flag covers the constraints
where its bit differs, and a certifying pair is two flags whose coverage unions to
everything. The pair search is made exact-but-cheap by branching on the rarest
constraint: any covering pair must contain a flag that covers it.
"""
import itertools
import json
import sys
import time

import stim

import flagsearch as FS

enc = FS.Encoder(stim.Circuit.from_file("encoder.stim"))
N = enc.n
NSITE = (N + 1) * 5


def site(t, d):
    return t * 5 + d


# ------------------------------------------------- fault traces over all sites
def base_faults_with_traces():
    """(label, residual_masks, xtrace, ztrace) for every Phase 3 gate-location fault."""
    tabs = []
    for op in enc.base:
        c = stim.Circuit()
        c.append("I", list(range(5)))
        c += op.circ
        tabs.append(stim.Tableau.from_circuit(c))
    out = []

    def run(label, slot, pstr):
        cur = stim.PauliString(pstr)
        xt = zt = 0
        for t in range(slot, N + 1):
            x, z = FS.masks(cur, 5)
            for d in range(5):
                if (x >> d) & 1:
                    xt |= 1 << site(t, d)
                if (z >> d) & 1:
                    zt |= 1 << site(t, d)
            if t < N:
                cur = tabs[t](cur)
        out.append((label, FS.masks(cur, 5), xt, zt))

    for i, op in enumerate(enc.base):
        for combo in FS.paulis_on(op.k):
            p = ["_"] * 5
            for q, ch in zip(op.support, combo):
                p[q] = ch
            run(f"g{i}:{op.label} {''.join(combo)}", i + 1, "".join(p))
    run("prep X on q5", 0, "____X")
    return out


t0 = time.time()
FAULTS = base_faults_with_traces()
print(f"{len(FAULTS)} Phase 3 gate-location faults traced in {time.time() - t0:.1f}s")

# cross-check against the tableau-based enumerator
ref = {lab: e for lab, e, _ in enc.faults(())}
assert all(ref[lab] == e for lab, e, _, _ in FAULTS if lab in ref), \
    "trace-based residuals disagree with the tableau enumerator"
print("residuals agree with the tableau enumerator")

# ------------------------------------------------------------- constraints
buckets = {}
for idx, (lab, e, _, _) in enumerate(FAULTS):
    buckets.setdefault(FS.syndrome(e), []).append(idx)
constraints = []
for syn, idxs in buckets.items():
    for a, b in itertools.combinations(idxs, 2):
        if FS.canon(FAULTS[a][1]) != FS.canon(FAULTS[b][1]):
            constraints.append((a, b))
NC = len(constraints)
print(f"{len(buckets)} syndrome classes, {NC} separation constraints")
worst = max(len({FS.canon(FAULTS[i][1]) for i in v}) for v in buckets.values())
print(f"worst syndrome class holds {worst} inequivalent residuals -> "
      f"at least {(worst - 1).bit_length()} flag bits are necessary")

# --------------------------------------------------- candidate flag masks
def flag_bits(kind, sites_mask):
    """bit vector over FAULTS, as an int"""
    bits = 0
    for i, (_, _, xt, zt) in enumerate(FAULTS):
        tr = xt if kind == "X" else zt
        if bin(tr & sites_mask).count("1") & 1:
            bits |= 1 << i
    return bits


def coverage(bits):
    m = 0
    for c, (a, b) in enumerate(constraints):
        if ((bits >> a) & 1) != ((bits >> b) & 1):
            m |= 1 << c
    return m


CAP4 = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
print(f"\nbuilding candidate flags (sizes 2 and 3 exhaustive, size 4 capped at {CAP4} "
      f"per kind)...")
t0 = time.time()
cands = []
for kind in ("X", "Z"):
    keys = FS.coupling_keys(enc, kind)
    for size in (2, 3, 4):
        for subset in FS.zero_sum_subsets(keys, size, cap=(CAP4 if size == 4 else None),
                                          primitive=(size > 2)):
            mask = 0
            for t, d in subset:
                mask |= 1 << site(t, d)
            cands.append((kind, subset, mask))
print(f"{len(cands)} prefiltered candidates in {time.time() - t0:.0f}s")

t0 = time.time()
cov = {}
for kind, subset, mask in cands:
    c = coverage(flag_bits(kind, mask))
    if c:
        cov.setdefault((kind, c), subset)
print(f"{len(cov)} distinct nonzero coverage patterns in {time.time() - t0:.0f}s")

FULL = (1 << NC) - 1
solo = [(c, k, s) for (k, c), s in cov.items() if c == FULL]
print(f"single flags covering every constraint: {len(solo)} (expected 0 by the bound)")

# ------------------------------------------------------- exact pair search
items = [(c, k, s) for (k, c), s in cov.items()]
best = None
rarest, rare_holders = None, None
for ci in range(NC):
    bit = 1 << ci
    holders = [i for i, (c, _, _) in enumerate(items) if c & bit]
    if rare_holders is None or len(holders) < len(rare_holders):
        rarest, rare_holders = ci, holders
print(f"rarest constraint is covered by {len(rare_holders)} of {len(items)} flags; "
      f"any certifying pair must contain one of them")

t0 = time.time()
found = []
for i in rare_holders:
    ci, ki, si = items[i]
    need = FULL & ~ci
    for j, (cj, kj, sj) in enumerate(items):
        if j == i:
            continue
        if cj & need == need:
            found.append(((ki, si), (kj, sj)))
            if len(found) >= 20:
                break
    if len(found) >= 20:
        break
print(f"pair search over {len(rare_holders)} x {len(items)} in {time.time() - t0:.0f}s")
print(f"pairs whose coverage unions to everything: {len(found)}")

summary = {"faults": len(FAULTS), "constraints": NC,
           "worst_class_size": worst, "min_flag_bits": (worst - 1).bit_length(),
           "candidates": len(cands), "distinct_coverages": len(cov),
           "single_flag_full_cover": len(solo), "covering_pairs_found": len(found)}

# ------------------------------------- full verification of covering pairs
verified = []
for (k1, s1), (k2, s2) in found:
    design = ((k1, tuple(s1)), (k2, tuple(s2)))
    f = enc.faults(design)
    if f is None:
        continue
    bad, nfl, ntot, buck, _ = FS.evaluate(f, False)
    verified.append((bad, design, nfl, ntot))
verified.sort()
summary["verified_best_bad"] = verified[0][0] if verified else None
print(f"\nfull enumeration on {len(found)} covering pairs "
      f"(this adds each gadget's own fault locations):")
for bad, design, nfl, ntot in verified[:5]:
    print(f"   bad={bad}  flags {nfl}/{ntot}  {design}")

json.dump(summary, open("results/step4_two_flag_summary.json", "w"), indent=2)

# --------------------------------------------- how many flag bits would suffice
print("\ngreedy set cover over the distinct coverage patterns:")
remaining = FULL
chosen = []
while remaining:
    best_i = max(range(len(items)), key=lambda i: bin(items[i][0] & remaining).count("1"))
    gain = bin(items[best_i][0] & remaining).count("1")
    if gain == 0:
        print("   no flag covers any remaining constraint; cover is impossible")
        break
    chosen.append(items[best_i])
    remaining &= ~items[best_i][0]
    print(f"   flag {len(chosen)}: kind {items[best_i][1]}, "
          f"{len(items[best_i][2])} couplings, covers {gain} more, "
          f"{bin(remaining).count('1')} constraints left")
summary["greedy_cover_size"] = len(chosen) if not remaining else None
if not remaining:
    print(f"   => {len(chosen)} flag bits suffice to separate every constraint")
    design = tuple((k, tuple(s2)) for _, k, s2 in chosen)
    f = enc.faults(design)
    if f is not None:
        bad, nfl, ntot, _, _ = FS.evaluate(f, False)
        print(f"   full enumeration of that {len(chosen)}-flag design: bad={bad}, "
              f"flags {nfl}/{ntot} locations")
        summary["greedy_design_bad"] = bad
        summary["greedy_design"] = str(design)
        if bad == 0:
            verified.append((bad, design, nfl, ntot))
            verified.sort()
    else:
        print("   that combination is not jointly valid")
        summary["greedy_design_bad"] = None

cert = [v for v in verified if v[0] == 0]
if cert:
    bad, design, nfl, ntot = cert[0]
    print(f"\nCERTIFYING TWO-FLAG DESIGN: {design}")
    _, _, _, buckets2, _ = FS.evaluate(enc.faults(design), False)
    lines = []
    for key in sorted(buckets2):
        e = FS.canon(buckets2[key][0][1])
        b = min(((e[0] ^ sx, e[1] ^ sz) for sx, sz in FS.STAB16),
                key=lambda c: sum(1 for i in range(5)
                                  if (c[0] >> i & 1) or (c[1] >> i & 1)))
        lines.append(f"syndrome {key[0]} flags {key[1]} -> {FS.pauli_str(b)} "
                     f"({len(buckets2[key])} fault locations)")
    print("\nSYNTHESIZED DECODER")
    for line in lines:
        print("   " + line)
    open("results/decoder_certificate.txt", "w").write("\n".join(lines) + "\n")
else:
    print("\nNo verified two-flag design certifies Phase 3.")
