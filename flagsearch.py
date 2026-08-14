"""Step 2 machinery: fault enumeration, flag validation, decoder synthesis.

ARITY-GENERIC. A fault location is a GATE, not an instruction, and a gate may act on
any number of qubits k. The location contributes all 4^k - 1 non-identity Paulis on its
support, so correlated multi-qubit faults are covered by construction:
  k=1 ->  3 faults      k=3 ->  63 faults      k=5 -> 1023 faults
  k=2 -> 15 faults      k=4 -> 255 faults
Sources of multi-qubit locations: native multi-qubit gates (Molmer-Sorensen, CCZ,
CCX), multi-qubit parity measurements (stim MPP), and user-declared macro blocks that
should be treated as one atomic noisy location.

Propagation is already arity-independent: we precompute, per slot, the image of each
single-qubit generator X_q and Z_q under the suffix circuit, so any fault Pauli's image
is an XOR of those. Cost per fault is O(k), not O(circuit).

No side effects on import.
"""
import itertools

import stim

import frames as F
from frames import ps

FLAG0 = 5
G = [ps(s) for s in F.OUT_STAB]
PAIRS = list(zip(F.IN_STAB, F.OUT_STAB)) + [(F.IN_X, F.OUT_X), (F.IN_Z, F.OUT_Z)]
CODE = {"X": (1, 0), "Y": (1, 1), "Z": (0, 1), "I": (0, 0)}


def masks(p, n):
    xs, zs = p.to_numpy()
    x = z = 0
    for i in range(n):
        if xs[i]:
            x |= 1 << i
        if zs[i]:
            z |= 1 << i
    return x, z


G_M = [masks(g, 5) for g in G]
XBAR_M, ZBAR_M = masks(ps(F.OUT_X), 5), masks(ps(F.OUT_Z), 5)
YBAR_M = (XBAR_M[0] ^ ZBAR_M[0], XBAR_M[1] ^ ZBAR_M[1])
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


ZERO = canon((0, 0))


def logical_class(e):
    if canon(e) == ZERO:
        return "I"
    for name, L in (("X", XBAR_M), ("Z", ZBAR_M), ("Y", YBAR_M)):
        if canon((e[0] ^ L[0], e[1] ^ L[1])) == ZERO:
            return name
    return "?"


def pauli_str(e):
    return "".join({(0, 0): "I", (1, 0): "X", (0, 1): "Z", (1, 1): "Y"}[
        ((e[0] >> i) & 1, (e[1] >> i) & 1)] for i in range(5))


# ============================================================ gate locations
class Op:
    """One atomic noisy location: a support (tuple of qubits, any length) and the
    circuit fragment that implements it."""

    __slots__ = ("label", "support", "circ")

    def __init__(self, label, support, circ):
        self.label = label
        self.support = tuple(support)
        self.circ = circ

    @property
    def k(self):
        return len(self.support)

    def __repr__(self):
        return f"Op({self.label}, k={self.k})"


def op_from_instruction(name, targets, nq):
    c = stim.Circuit()
    c.append("I", list(range(nq)))
    c.append(name, list(targets))
    return Op(f"{name}{tuple(targets)}", targets, c)


def gate_arity(name, overrides=None):
    """Qubits consumed per gate. Uses stim's gate metadata, with an override hook for
    gates stim does not model natively (CCZ, CCX, MS, custom macros)."""
    if overrides and name in overrides:
        return overrides[name]
    try:
        gd = stim.gate_data(name)
    except (IndexError, KeyError, ValueError):
        gd = None
    if gd is not None:
        if gd.is_two_qubit_gate:
            return 2
        if gd.is_single_qubit_gate:
            return 1
    raise ValueError(
        f"arity of gate {name!r} is not determined by stim metadata; pass "
        f"arity_overrides={{{name!r}: k}} or wrap it in a macro Op")


def split_ops(circuit, arity_overrides=None, nq=None):
    """One Op per gate. Stim batches targets ('H 1 2' is TWO 1-qubit gates,
    'CX 0 1 0 4' is TWO CX gates), and MPP batches Pauli products with combiners.
    Arity comes from gate metadata, so k-qubit gates split correctly for any k."""
    flat = circuit.flattened()
    nq = nq if nq is not None else flat.num_qubits
    ops = []
    for inst in flat:
        tg = inst.targets_copy()
        if inst.name == "MPP":
            group, prod = [], []
            for t in tg:
                if t.is_combiner:
                    continue
                prod.append(t)
                group.append(t.qubit_value)
            # stim separates products by absence of a combiner; rebuild explicitly
            products, cur = [], []
            i = 0
            while i < len(tg):
                cur = [tg[i]]
                i += 1
                while i < len(tg) and tg[i].is_combiner:
                    cur.append(tg[i + 1])
                    i += 2
                products.append(cur)
            for prod in products:
                sup = [t.qubit_value for t in prod]
                c = stim.Circuit()
                c.append("I", list(range(nq)))
                ops.append(Op(f"MPP{tuple(sup)}", sup, c))  # measurement: no unitary action
            continue
        k = gate_arity(inst.name, arity_overrides)
        vals = [t.value for t in tg]
        for i in range(0, len(vals), k):
            chunk = vals[i:i + k]
            ops.append(op_from_instruction(inst.name, chunk, nq))
    return ops


def macro_ops(ops, groups):
    """Fuse selected consecutive Ops into single atomic k-qubit locations.
    groups: list of (start, stop) index ranges into ops. Use for native multi-qubit
    gates compiled into Clifford fragments, where the whole fragment fails at once."""
    out, i = [], 0
    gs = sorted(groups)
    while i < len(ops):
        hit = next((g for g in gs if g[0] == i), None)
        if hit:
            a, b = hit
            sup = sorted({q for op in ops[a:b] for q in op.support})
            c = stim.Circuit()
            for op in ops[a:b]:
                c += op.circ
            out.append(Op(f"MACRO[{a}:{b}]", sup, c))
            i = b
        else:
            out.append(ops[i])
            i += 1
    return out


def paulis_on(k, max_weight=None):
    """All 4^k - 1 non-identity Paulis on a k-qubit support, optionally restricted to
    weight <= max_weight. Restriction is the caller's decision and is reported by
    fault_model_summary so it can never be a silent cap."""
    for combo in itertools.product("IXYZ", repeat=k):
        if all(c == "I" for c in combo):
            continue
        if max_weight is not None and sum(1 for c in combo if c != "I") > max_weight:
            continue
        yield combo


def normalize(design):
    """A flag is (kind, couplings) with couplings = ((slot, qubit), ...) and at least two
    of them. The legacy bracketing-pair form (kind, d, t1, t2) is still accepted."""
    out = []
    for f in design:
        if len(f) == 4 and isinstance(f[1], int):
            kind, d, t1, t2 = f
            out.append((kind, ((t1, d), (t2, d))))
        else:
            out.append((f[0], tuple((int(t), int(q)) for t, q in f[1])))
    return tuple(out)


# ==================================================================== encoder
class Encoder:
    def __init__(self, circuit, pairs=None, arity_overrides=None, macros=None, nq=None):
        base_nq = nq if nq is not None else max(5, circuit.flattened().num_qubits)
        self.base = split_ops(circuit, arity_overrides, base_nq)
        if macros:
            self.base = macro_ops(self.base, macros)
        self.n = len(self.base)
        self.pairs = pairs or PAIRS
        self.ncx = sum(1 for op in self.base if op.k == 2)
        self.arity_histogram = {}
        for op in self.base:
            self.arity_histogram[op.k] = self.arity_histogram.get(op.k, 0) + 1

    def fault_model_summary(self, max_weight=None):
        parts = []
        total = 0
        for k in sorted(self.arity_histogram):
            n = self.arity_histogram[k]
            per = sum(1 for _ in paulis_on(k, max_weight))
            full = 4 ** k - 1
            total += n * per
            note = "" if per == full else f" (restricted from {full} by max_weight)"
            parts.append(f"{n} location(s) of arity {k} x {per} Paulis{note}")
        return f"{total} gate-location faults: " + "; ".join(parts)

    def build(self, design):
        ins = {}
        design = normalize(design)
        nq = 5 + len(design)
        for k, (kind, coups) in enumerate(design):
            f = FLAG0 + k
            for t, d in coups:
                tg = [d, f] if kind == "X" else [f, d]
                ins.setdefault(t, []).append(op_from_instruction("CX", tg, nq))
        ops = []
        for i in range(self.n + 1):
            ops.extend(ins.get(i, []))
            if i < self.n:
                ops.append(self.base[i])
        return ops

    def images(self, ops, nq):
        ident = stim.Circuit()
        ident.append("I", list(range(nq)))
        tabs = [None] * (len(ops) + 1)
        tabs[len(ops)] = stim.Tableau.from_circuit(ident)
        for i in range(len(ops) - 1, -1, -1):
            c = stim.Circuit()
            c.append("I", list(range(nq)))
            c += ops[i].circ
            tabs[i] = stim.Tableau.from_circuit(c).then(tabs[i + 1])
        IMG = [[(masks(t.x_output(q), nq), masks(t.z_output(q), nq)) for q in range(nq)]
               for t in tabs]
        return tabs, IMG

    def valid(self, design, tabs, nq):
        full = tabs[0]
        for k, (kind, coups) in enumerate(normalize(design)):
            meas = stim.PauliString(nq)
            meas[FLAG0 + k] = 3 if kind == "X" else 1
            if full(meas) != meas:
                return False
        for src, want in self.pairs:
            if full(stim.PauliString(src + "_" * (nq - 5))) != \
               stim.PauliString(want + "_" * (nq - 5)):
                return False
        return True

    def faults(self, design, include_idle=False, max_weight=None):
        ops = self.build(design)
        nq = 5 + len(design)
        tabs, IMG = self.images(ops, nq)
        if design and not self.valid(design, tabs, nq):
            return None
        kinds = [k for k, _ in normalize(design)]
        out = []

        def emit(label, slot, comps):
            x = z = 0
            for q, c in comps:
                cx, cz = CODE[c]
                if cx:
                    ix, iz = IMG[slot][q][0]
                    x ^= ix
                    z ^= iz
                if cz:
                    ix, iz = IMG[slot][q][1]
                    x ^= ix
                    z ^= iz
            flags = tuple(1 if ((x if kinds[k] == "X" else z) >> (FLAG0 + k)) & 1 else 0
                          for k in range(len(design)))
            out.append((label, (x & 31, z & 31), flags))

        for i, op in enumerate(ops):
            for combo in paulis_on(op.k, max_weight):
                emit(f"g{i}:{op.label} {''.join(combo)}", i + 1,
                     [(q, c) for q, c in zip(op.support, combo) if c != "I"])
        emit("prep X on q5", 0, [(4, "X")])
        for k, (kind, coups) in enumerate(normalize(design)):
            emit(f"prep flag{k}", 0, [(FLAG0 + k, "X" if kind == "X" else "Z")])
        if include_idle:
            for slot in range(len(ops) + 1):
                for q in range(nq):
                    for P in "XYZ":
                        if slot == 0 and ((q == 4 and P in "ZY") or q >= FLAG0):
                            continue
                        emit(f"idle s{slot} {P}q{q}", slot, [(q, P)])
        for k in range(len(design)):
            fl = [0] * len(design)
            fl[k] = 1
            out.append((f"flag{k} readout flip", (0, 0), tuple(fl)))
        return out


def evaluate(faults, discard_on_flag):
    buckets = {}
    for label, e, fl in faults:
        if discard_on_flag and any(fl):
            continue
        buckets.setdefault((syndrome(e), fl), []).append((label, e))
    bad = [k for k, v in buckets.items() if len({canon(e) for _, e in v}) > 1]
    return len(bad), sum(1 for _, _, fl in faults if any(fl)), len(faults), buckets, bad


def single_flag_search(enc, include_idle=False, max_weight=None, strict_only=False):
    """returns (n_valid, best_strict, best_postsel); best_* = (bad_buckets, design, nflag)"""
    nvalid = 0
    bestA = bestB = None
    for kind in ("X", "Z"):
        for d in range(5):
            for t1 in range(enc.n + 1):
                for t2 in range(t1 + 1, enc.n + 1):
                    design = ((kind, d, t1, t2),)
                    f = enc.faults(design, include_idle, max_weight)
                    if f is None:
                        continue
                    nvalid += 1
                    badA, nfl, ntot, _, _ = evaluate(f, False)
                    if bestA is None or badA < bestA[0]:
                        bestA = (badA, design, nfl)
                    if strict_only:
                        continue
                    badB, _, _, _, _ = evaluate(f, True)
                    if bestB is None or badB < bestB[0]:
                        bestB = (badB, design, nfl)
    return nvalid, bestA, bestB


# ================================================ widened flag family search
def coupling_keys(enc, kind):
    """For a flag of the given kind, the DATA part of the measured flag operator's image
    is the product over couplings of the base-suffix image of one generator:

      kind 'X': f is the CNOT target, so Z_f -> Z_d Z_f at each coupling; the key is the
                base-suffix image of Z_d.
      kind 'Z': f is the CNOT control, so X_f -> X_f X_d at each coupling; the key is the
                base-suffix image of X_d.

    Validity requires the flag readout to be deterministic in the fault-free run, so that
    data part must vanish: the XOR of the keys over all couplings must be zero. That is a
    necessary condition, checkable with two integer XORs per coupling and no tableau, and
    it is what makes the widened family tractable. Sufficiency is still decided by
    Encoder.valid()."""
    ident = stim.Circuit()
    ident.append("I", list(range(5)))
    tabs = [None] * (enc.n + 1)
    tabs[enc.n] = stim.Tableau.from_circuit(ident)
    for i in range(enc.n - 1, -1, -1):
        c = stim.Circuit()
        c.append("I", list(range(5)))
        c += enc.base[i].circ
        tabs[i] = stim.Tableau.from_circuit(c).then(tabs[i + 1])
    keys = {}
    for t in range(enc.n + 1):
        for d in range(5):
            gen = tabs[t].z_output(d) if kind == "X" else tabs[t].x_output(d)
            keys[(t, d)] = masks(gen, 5)
    return keys


def _has_zero_sum_proper_subset(keys, subset):
    """True if some proper sub-subset already cancels, i.e. the design is just a smaller
    flag with redundant couplings bolted on rather than a genuinely new gadget."""
    for r in range(2, len(subset)):
        for sub in itertools.combinations(subset, r):
            x = z = 0
            for it in sub:
                kx, kz = keys[it]
                x ^= kx
                z ^= kz
            if (x, z) == (0, 0):
                return True
    return False


def zero_sum_subsets(keys, size, cap=None, primitive=False):
    """All subsets of `size` couplings whose keys XOR to zero. With primitive=True,
    subsets containing a smaller cancelling subset are skipped."""
    items = sorted(keys)
    n = len(items)
    found = 0
    if size == 2:
        by_key = {}
        for it in items:
            by_key.setdefault(keys[it], []).append(it)
        for group in by_key.values():
            for a, b in itertools.combinations(group, 2):
                yield (a, b)
                found += 1
                if cap and found >= cap:
                    return
    elif size == 3:
        by_key = {}
        for it in items:
            by_key.setdefault(keys[it], []).append(it)
        for i in range(n):
            for j in range(i + 1, n):
                ka, kb = keys[items[i]], keys[items[j]]
                need = (ka[0] ^ kb[0], ka[1] ^ kb[1])
                for c in by_key.get(need, ()):
                    if c > items[j]:
                        cand = (items[i], items[j], c)
                        if primitive and _has_zero_sum_proper_subset(keys, cand):
                            continue
                        yield cand
                        found += 1
                        if cap and found >= cap:
                            return
    elif size == 4:
        pair_key = {}
        for i in range(n):
            for j in range(i + 1, n):
                ka, kb = keys[items[i]], keys[items[j]]
                pair_key.setdefault((ka[0] ^ kb[0], ka[1] ^ kb[1]), []).append(
                    (items[i], items[j]))
        for group in pair_key.values():
            for (a, b), (c, d) in itertools.combinations(group, 2):
                if len({a, b, c, d}) == 4:
                    cand = tuple(sorted((a, b, c, d)))
                    if primitive and _has_zero_sum_proper_subset(keys, cand):
                        continue
                    yield cand
                    found += 1
                    if cap and found >= cap:
                        return
    else:
        raise ValueError("size must be 2, 3 or 4")


def wide_search(enc, sizes=(2, 3, 4), kinds=("X", "Z"), cap=None, log=print,
                primitive=True):
    """Search the widened single-flag family. Returns (stats, results) where results is
    a list of (bad_buckets, design, n_flagged, n_faults) sorted best first."""
    results = []
    stats = {}
    for kind in kinds:
        keys = coupling_keys(enc, kind)
        for size in sizes:
            n_cand = n_valid = 0
            for subset in zero_sum_subsets(keys, size, cap, primitive):
                n_cand += 1
                design = ((kind, tuple(subset)),)
                f = enc.faults(design)
                if f is None:
                    continue
                n_valid += 1
                bad, nfl, ntot, _, _ = evaluate(f, False)
                results.append((bad, design, nfl, ntot))
            stats[(kind, size)] = (n_cand, n_valid)
            if log:
                log(f"   kind {kind}, {size} couplings: {n_cand} passed the algebraic "
                    f"prefilter, {n_valid} are valid flags")
    results.sort(key=lambda r: (r[0], len(r[1][0][1])))
    return stats, results
