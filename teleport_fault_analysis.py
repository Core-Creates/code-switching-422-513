"""Fault analysis of the joint logical measurement M1 = XXII (x) XXXXX.

This is the only object in the teleportation switch that needs protecting, and it is a
Pauli product measurement rather than an encoding cascade. That distinction is the whole
story:

  In a measurement cascade every gate is CX(m -> data) with the SAME control m, and a
  flag gadget is CX(m -> f). Gates sharing a control commute, so the flag pair cancels
  exactly, for ANY bracketing. In the re-encoding cascade the intervening gates did not
  commute with the flag pair, which is why only 3474 of 9900 bracketings were even valid
  flags there, and why the family was too weak. Here every bracketing is valid by
  construction.

Accounting for one round. A fault can do four things, and all four are tracked:
  * leave a Pauli residual on B, which the [[5,1,3]] syndrome must handle
  * leave a residual on A, which the destructive Z-basis readout of A may detect via the
    ZZZZ parity check, since A is measured out anyway
  * flip the M1 outcome, misapplying the Zbar frame Pauli on B
  * flip the M2 = Z1bar parity, misapplying the Xbar frame Pauli on B
The effective logical error on B is residual_B times Xbar^(dM2) times Zbar^(dM1).

A is read out destructively in the Z basis, which costs no two-qubit gates and gives the
ZZZZ stabilizer as a free check: any odd-weight X-type error on A is detected and the
shot is discarded. Post-selection is already the regime (Lemma 1), so discarding is
allowed; what may not happen is an undetected, unflagged, uncorrectable error on B.
"""
import itertools
import json

import stim

import frames as F
from frames import ps

A = [0, 1, 2, 3]
B = [4, 5, 6, 7, 8]
M, FLAG = 9, 10
NQ = 11
SUPPORT = [0, 1] + B          # support of M1 = XXII (x) XXXXX
Z1BAR_SUPPORT = [0, 2]        # ZIZI

G = [ps(s) for s in F.OUT_STAB]
G_M = [(sum(((str(g)[1:][i] in "XY") << i) for i in range(5)),
        sum(((str(g)[1:][i] in "ZY") << i) for i in range(5))) for g in G]
XBAR_M = (0b11111, 0)
ZBAR_M = (0, 0b11111)
STAB16 = []
for bits in itertools.product([0, 1], repeat=4):
    x = z = 0
    for b, (gx, gz) in zip(bits, G_M):
        if b:
            x ^= gx
            z ^= gz
    STAB16.append((x, z))


def sympl(a, b):
    return bin((a[0] & b[1]) ^ (a[1] & b[0])).count("1") & 1


def syndrome(e):
    return tuple(sympl(e, g) for g in G_M)


def canon(e):
    return min((e[0] ^ sx, e[1] ^ sz) for sx, sz in STAB16)


def build(order, brackets):
    """order: sequence of the 7 supported qubits. brackets: (i, j) slot indices for the
    flag CNOT pair, 0 <= i < j <= 7. Returns the op list."""
    ops = []
    ops.append(("H", [M]))
    for slot in range(len(order) + 1):
        if brackets and slot == brackets[0]:
            ops.append(("CX", [M, FLAG]))
        if slot < len(order):
            ops.append(("CX", [M, order[slot]]))
        if brackets and slot == brackets[1]:
            ops.append(("CX", [M, FLAG]))
    ops.append(("H", [M]))
    return ops


def state_generators():
    """Stabilizer generators of the joint state before the cascade. A's payload logical
    is unknown, so it is deliberately NOT a generator: an error is trivial only if it acts
    as the identity for EVERY payload."""
    g = []
    for st in ("XXXX", "ZZZZ", "ZZII"):
        g.append("".join(st[A.index(q)] if q in A else "_" for q in range(NQ)))
    for st in list(F.OUT_STAB) + [F.OUT_Z]:
        g.append("".join(st[B.index(q)] if q in B else "_" for q in range(NQ)))
    g.append("".join("Z" if q == M else "_" for q in range(NQ)))     # ancilla reset to |0>;
    # the circuit's own H makes it |+>, so declaring |+> here would double-count the prep
    g.append("".join("Z" if q == FLAG else "_" for q in range(NQ)))  # flag in |0>
    return [stim.PauliString(x) for x in g]


def reduce_mod(vecs, target):
    """Canonical representative of target modulo the span of vecs, over GF(2).

    Two errors that differ by an element of the state's stabilizer group are the SAME
    physical fault: Y on an ancilla stabilized by X is just Z, and an error inside the
    group is no error at all. Reducing before propagating is what makes the fault count
    physical rather than formal."""
    rows = [(v[0] << NQ) | v[1] for v in vecs]
    t = (target[0] << NQ) | target[1]
    basis = []
    for r in rows:
        for b in basis:
            r = min(r, r ^ b)
        if r:
            basis.append(r)
            basis.sort(reverse=True)
    for b in basis:
        t = min(t, t ^ b)
    return (t >> NQ) & ((1 << NQ) - 1), t & ((1 << NQ) - 1)


def to_pauli(xz):
    x, z = xz
    return stim.PauliString("".join(
        {(0, 0): "_", (1, 0): "X", (0, 1): "Z", (1, 1): "Y"}[((x >> i) & 1, (z >> i) & 1)]
        for i in range(NQ)))


def analyze(order, brackets, repetition=True):
    ops = []
    for name, tg in build(order, brackets):
        c = stim.Circuit()
        c.append("I", range(NQ))
        c.append(name, tg)
        ops.append((name, tg, c))
    tabs = [None] * (len(ops) + 1)
    ident = stim.Circuit()
    ident.append("I", range(NQ))
    tabs[len(ops)] = stim.Tableau.from_circuit(ident)
    for i in range(len(ops) - 1, -1, -1):
        tabs[i] = stim.Tableau.from_circuit(ops[i][2]).then(tabs[i + 1])
    if brackets:
        # the flag pair must cancel: fault-free readout deterministic, data untouched
        zf = stim.PauliString(NQ)
        zf[FLAG] = 3
        if tabs[0](zf) != zf:
            return None, None, None, None
        n_flag_cnots = sum(1 for n, tg in build(order, brackets) if tg == [M, FLAG])
        if n_flag_cnots != 2:
            return None, None, None, None

    def masks(p):
        s = str(p)[1:]
        x = sum((s[i] in "XY") << i for i in range(NQ))
        z = sum((s[i] in "ZY") << i for i in range(NQ))
        return x, z

    # stabilizer generators of the state at each slot, for the triviality filter
    gens0 = state_generators()
    prefix = [None] * (len(ops) + 1)
    cur = stim.Tableau.from_circuit(ident)
    prefix[0] = cur
    for i, (_, _, cc) in enumerate(ops):
        cur = cur.then(stim.Tableau.from_circuit(cc))
        prefix[i + 1] = cur
    def ancilla_local(gens):
        """Basis of group elements supported ONLY on the ancillas m and flag.

        Reduction must be restricted to these. A stabilizer touching the data blocks,
        Zbar_B for instance, does act trivially on the pre-measurement state, but the
        residual-plus-frame bookkeeping below is written in terms of an error on the
        payload-carrying block, and multiplying by Zbar_B silently relabels the logical
        class. Ancilla-local elements have no such ambiguity."""
        DATA = [q for q in range(NQ) if q not in (M, FLAG)]
        rows = [((sum(((g[0] >> q) & 1) << i for i, q in enumerate(DATA))
                  | sum(((g[1] >> q) & 1) << (len(DATA) + i) for i, q in enumerate(DATA))),
                 g) for g in gens]
        basis, out = [], []
        for key, g in rows:
            cur, acc = key, g
            for bkey, bacc in basis:
                if cur ^ bkey < cur:
                    cur ^= bkey
                    acc = (acc[0] ^ bacc[0], acc[1] ^ bacc[1])
            if cur:
                basis.append((cur, acc))
                basis.sort(key=lambda t: -t[0])
            else:
                out.append(acc)
        return out

    state_gens = [ancilla_local([masks(prefix[s](g)) for g in gens0])
                  for s in range(len(ops) + 1)]

    records = []
    n_trivial = 0

    def emit(label, slot, comps, force_m1=False, force_flag=False):
        nonlocal n_trivial
        p = ["_"] * NQ
        for q, ch in comps:
            p[q] = ch
        raw = stim.PauliString("".join(p))
        if comps:
            red = reduce_mod(state_gens[slot], masks(raw))
            if red == (0, 0):
                n_trivial += 1    # acts as the identity on the state: not a fault
                return
            raw = to_pauli(red)   # same physical fault, canonical representative
        x, z = masks(tabs[slot](raw))
        # flag readout (Z basis on |0>) flips on X or Y at FLAG
        flag = ((x >> FLAG) & 1) or force_flag
        # M1 readout is X basis on m; flips on Z or Y at M
        dm1 = (((z >> M) & 1) or force_m1) & 1
        # A readout is destructive Z basis; X-type support flips outcome bits
        ax = (x >> 0) & 0b1111
        detected = bin(ax).count("1") & 1          # ZZZZ parity check on A
        dm2 = bin(ax & 0b0101).count("1") & 1      # Z1bar = Z on q1 and q3
        eb = ((x >> 4) & 31, (z >> 4) & 31)
        if repetition:
            dm1 = 0 if (eb == (0, 0) and not detected and dm2 == 0) else dm1
        if dm1:
            eb = (eb[0] ^ ZBAR_M[0], eb[1] ^ ZBAR_M[1])
        if dm2:
            eb = (eb[0] ^ XBAR_M[0], eb[1] ^ XBAR_M[1])
        records.append((label, eb, int(bool(flag)), int(detected)))

    P2 = [a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II"]
    for i, (name, tg, _) in enumerate(ops):
        if len(tg) == 2:
            for pp in P2:
                emit(f"g{i}:{name}{tuple(tg)} {pp}", i + 1, [(tg[0], pp[0]), (tg[1], pp[1])])
        else:
            for pch in "XYZ":
                emit(f"g{i}:{name}({tg[0]}) {pch}", i + 1, [(tg[0], pch)])
    for pch in "XYZ":                             # the filter drops the trivial ones
        emit(f"prep {pch} on m", 0, [(M, pch)])
    if brackets:
        for pch in "XYZ":
            emit(f"prep {pch} on flag", 0, [(FLAG, pch)])
        emit("flag readout flip", len(ops), [], force_flag=True)
    emit("M1 readout flip", len(ops), [], force_m1=True)

    kept = [(lab, eb) for lab, eb, fl, det in records if not fl and not det]
    analyze.n_trivial = n_trivial
    buckets = {}
    for lab, eb in kept:
        buckets.setdefault(syndrome(eb), []).append((lab, eb))
    bad = [k for k, v in buckets.items() if len({canon(e) for _, e in v}) > 1]
    return records, kept, buckets, bad


DEFAULT_ORDER = [4, 5, 6, 7, 8, 0, 1]
print("Joint measurement M1 = XXII (x) XXXXX, one ancilla cascade of 7 CNOTs\n")

for label, brackets in (("no flag", None), ("one flag bracketing the whole cascade", (0, 7))):
    recs, kept, buckets, bad = analyze(DEFAULT_ORDER, brackets)
    assert recs is not None, "invalid flag gadget"
    disc = len(recs) - len(kept)
    print(f"{label}:")
    print(f"   {analyze.n_trivial} candidate faults act as the identity on the state "
          f"and are excluded")
    print(f"   {len(recs)} single-fault locations, {disc} discarded "
          f"(flag or A parity check), {len(kept)} surviving")
    print(f"   {len(buckets)} syndrome buckets on B, {len(bad)} undecodable "
          f"-> {'FAULT TOLERANT' if not bad else 'NOT fault tolerant'}")
    if bad:
        for k in bad[:3]:
            reps = {}
            for lab, e in buckets[k]:
                reps.setdefault(canon(e), lab)
            print(f"      syndrome {k}: " + "  vs  ".join(list(reps.values())[:3]))
    print()

print("=" * 74)
print("Search over coupling orders and flag brackets")
print("=" * 74)
best = None
n_ok = 0
n_tried = 0
ORDERS = [list(o) for o in itertools.permutations(SUPPORT)][::37]   # deterministic sample
ORDERS.insert(0, DEFAULT_ORDER)
BRACKETS = [(i, j) for i in range(8) for j in range(i + 1, 8)]
print(f"sampling {len(ORDERS)} of {5040} coupling orders x {len(BRACKETS)} brackets "
      f"= {len(ORDERS) * len(BRACKETS)} designs (the sample is a logged bound)")
for order in ORDERS:
    for brackets in BRACKETS:
        n_tried += 1
        recs, kept, buckets, bad = analyze(list(order), brackets)
        if recs is None:
            continue
        if not bad:
            n_ok += 1
            disc = len(recs) - len(kept)
            if best is None or disc < best[0]:
                best = (disc, list(order), brackets, len(recs), len(kept), buckets)
print(f"certifying (order, bracket) designs found: {n_ok}")
if best:
    disc, order, brackets, ntot, nkept, buckets = best
    print(f"\nBEST: coupling order {order}, flag bracket {brackets}")
    print(f"   {ntot} fault locations, {disc} discarded, {nkept} surviving, "
          f"all {len(buckets)} syndrome buckets decodable")
    lines = []
    for key in sorted(buckets):
        e = canon(buckets[key][0][1])
        b = min(((e[0] ^ sx, e[1] ^ sz) for sx, sz in STAB16),
                key=lambda c: sum(1 for i in range(5)
                                  if (c[0] >> i & 1) or (c[1] >> i & 1)))
        s = "".join({(0, 0): "I", (1, 0): "X", (0, 1): "Z", (1, 1): "Y"}[
            ((b[0] >> i) & 1, (b[1] >> i) & 1)] for i in range(5))
        lines.append(f"syndrome {key} -> correct {s} ({len(buckets[key])} fault locations)")
    print("\n   SYNTHESIZED DECODER")
    for line in lines:
        print("      " + line)
    open("results/teleport_decoder_certificate.txt", "w").write("\n".join(lines) + "\n")
    json.dump({"order": order, "brackets": list(brackets), "locations": ntot,
               "discarded": disc, "surviving": nkept, "buckets": len(buckets),
               "certifying_designs_found": n_ok},
              open("results/teleport_certificate.json", "w"), indent=2)
else:
    print("\nNo (order, bracket) design certifies the joint measurement.")
