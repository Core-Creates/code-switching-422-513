"""The |0>_L factory for block B, the last unproven piece of the teleportation switch.

A structural simplification decides the difficulty of this step. Block B does not need to
be in |0>_L specifically. The teleportation identity verified in teleport_switch.py
carries the frame Pauli Xbar^(m2 + b5) Zbar^(m1), where b5 is the recorded outcome of the
Zbar measurement on B. So B need only be IN THE CODE SPACE; which of the two logical
states it holds is recorded, not required. Consequently:

  * an error that anticommutes with some g_i is DETECTED by the verification syndrome,
    and the shot is discarded, which is allowed since this is a post-selected factory
  * an error that commutes with all g_i is either a stabilizer, hence no error at all,
    or a logical operator, hence absorbed by the frame bit b5

There is no third case. Preparation therefore cannot produce an undetected logical fault
on its own, and the only real question is whether the VERIFICATION cascades inject errors,
which is the same question the joint measurement answered, with the same flag argument
available because the gates again share the ancilla as control.

This file establishes both halves computationally rather than asserting them.
"""
import itertools
import json

import stim

import frames as F
from frames import ps

BLK = [0, 1, 2, 3, 4]
G = [ps(s) for s in F.OUT_STAB]
XBAR, ZBAR = ps(F.OUT_X), ps(F.OUT_Z)


def masks(p, n):
    s = str(p)[1:]
    return (sum((s[i] in "XY") << i for i in range(n)),
            sum((s[i] in "ZY") << i for i in range(n)))


G_M = [masks(g, 5) for g in G]
STAB16 = []
for bits in itertools.product([0, 1], repeat=4):
    x = z = 0
    for b, (gx, gz) in zip(bits, G_M):
        if b:
            x ^= gx
            z ^= gz
    STAB16.append((x, z))
XB_M, ZB_M = masks(XBAR, 5), masks(ZBAR, 5)


def sympl(a, b):
    return bin((a[0] & b[1]) ^ (a[1] & b[0])).count("1") & 1


def syndrome(e):
    return tuple(sympl(e, g) for g in G_M)


def in_stab(e):
    return any(e == s for s in STAB16)


def classify(e):
    """'I' stabilizer, 'X'/'Y'/'Z' logical, 'detected' if the syndrome is nontrivial."""
    if any(syndrome(e)):
        return "detected"
    if in_stab(e):
        return "I"
    for name, L in (("X", XB_M), ("Z", ZB_M), ("Y", (XB_M[0] ^ ZB_M[0], XB_M[1] ^ ZB_M[1]))):
        if in_stab((e[0] ^ L[0], e[1] ^ L[1])):
            return name
    return "?"


# ------------------------------------------------------- 1. synthesize the prep
def prep_circuit():
    """A circuit taking |00000> to |0>_L. Only the Z-images matter for a state, so we
    take the cheaper graph-state synthesis rather than a full Clifford."""
    zs = [ps(F.OUT_Z)] + [ps(s) for s in F.OUT_STAB]
    xs = F.symplectic_completion(zs)
    T = stim.Tableau.from_conjugated_generators(xs=xs, zs=zs)
    best = None
    for method in ("elimination", "graph_state"):
        c = T.to_circuit(method=method)
        n2 = sum(len(i.targets_copy()) // 2 for i in c.flattened()
                 if i.name in ("CX", "CZ", "CY", "SWAP"))
        if best is None or n2 < best[1]:
            best = (c, n2, method)
    return best


circ, n2, method = prep_circuit()
sim = stim.TableauSimulator()
sim.do(circ)
stabs = sim.canonical_stabilizers()
want = stim.Tableau.from_stabilizers([ps(s) for s in F.OUT_STAB] + [ps(F.OUT_Z)],
                                     allow_redundant=False, allow_underconstrained=False)
sim2 = stim.TableauSimulator()
sim2.do_tableau(want, BLK)
print(f"prep circuit ({method}): {n2} two-qubit gates, {len(circ.flattened())} instructions")
got = {str(s) for s in stabs}
exp = {str(s) for s in sim2.canonical_stabilizers()}
print(f"prepares the correct state: {got == exp}")
assert got == exp, "prep circuit does not produce |0>_L"

# --------------------------- 2. every prep fault is detected or absorbed by the frame
RESETS = {"R": "Z", "RZ": "Z", "RX": "X", "RY": "Y"}
ops = []
init_basis = {}
for inst in circ.flattened():
    tg = [t.value for t in inst.targets_copy()]
    if inst.name in RESETS:
        for q in tg:
            init_basis[q] = RESETS[inst.name]     # state after the reset
        continue
    if inst.name in ("CX", "CZ", "CY", "SWAP"):
        for a, b in zip(tg[::2], tg[1::2]):
            ops.append((inst.name, [a, b]))
    else:
        for q in tg:
            ops.append((inst.name, [q]))
assert len(init_basis) == 5, "every qubit must be initialised"

tabs = [None] * (len(ops) + 1)
ident = stim.Circuit()
ident.append("I", BLK)
tabs[len(ops)] = stim.Tableau.from_circuit(ident)
for i in range(len(ops) - 1, -1, -1):
    c = stim.Circuit()
    c.append("I", BLK)
    c.append(ops[i][0], ops[i][1])
    tabs[i] = stim.Tableau.from_circuit(c).then(tabs[i + 1])

tally = {}
for i, (name, tg) in enumerate(ops):
    combos = ([a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II"]
              if len(tg) == 2 else list("XYZ"))
    for combo in combos:
        p = ["_"] * 5
        for q, ch in zip(tg, combo):
            if ch != "I":
                p[q] = ch
        e = masks(tabs[i + 1](stim.PauliString("".join(p))), 5)
        tally[classify(e)] = tally.get(classify(e), 0) + 1

# preparation faults: the Pauli matching the reset basis acts trivially on that qubit
for q, basis in init_basis.items():
    for pch in "XYZ":
        if pch == basis:
            continue
        p = ["_"] * 5
        p[q] = pch
        e = masks(tabs[0](stim.PauliString("".join(p))), 5)
        tally[classify(e)] = tally.get(classify(e), 0) + 1
print(f"\nsingle faults in the prep circuit, by outcome: {tally}")
assert "?" not in tally, "an error escaped classification"
absorbed = sum(v for k, v in tally.items() if k in ("X", "Y", "Z"))
print(f"   detected by the g1..g4 syndrome and discarded: {tally.get('detected', 0)}")
print(f"   stabilizer, so not an error at all:            {tally.get('I', 0)}")
print(f"   logical, absorbed by the recorded frame bit:   {absorbed}")
print("   uncorrectable:                                  0")
print("\n=> preparation cannot produce an undetected fault. Verification post-selection")
print("   plus the frame bit covers every case, because B need only be in the code")
print("   space, not in a particular logical state.")

# ------------------------- 3. the verification cascades, flag-protected
ANC, FLG = 5, 6
NQ = 7


def verify_round(gen, bracket=(0, 4)):
    """Measure one weight-4 generator with an ancilla cascade, optionally flagged.
    Returns the fault records: (label, residual on block, flag, syndrome-flip)."""
    s = str(ps(gen))[1:]
    terms = [(i, s[i]) for i in range(5) if s[i] != "_"]
    gates = [("H", [ANC])]
    for slot in range(len(terms) + 1):
        if bracket and slot == bracket[0]:
            gates.append(("CX", [ANC, FLG]))
        if slot < len(terms):
            q, pauli = terms[slot]
            gates.append(({"X": "CX", "Z": "CZ", "Y": "CY"}[pauli], [ANC, q]))
        if bracket and slot == bracket[1]:
            gates.append(("CX", [ANC, FLG]))
    gates.append(("H", [ANC]))

    tb = [None] * (len(gates) + 1)
    idn = stim.Circuit()
    idn.append("I", range(NQ))
    tb[len(gates)] = stim.Tableau.from_circuit(idn)
    for i in range(len(gates) - 1, -1, -1):
        c = stim.Circuit()
        c.append("I", range(NQ))
        c.append(gates[i][0], gates[i][1])
        tb[i] = stim.Tableau.from_circuit(c).then(tb[i + 1])
    if bracket:
        zf = stim.PauliString(NQ)
        zf[FLG] = 3
        assert tb[0](zf) == zf, "flag pair does not cancel"

    recs = []
    for i, (name, tg) in enumerate(gates):
        combos = ([a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II"]
                  if len(tg) == 2 else list("XYZ"))
        for combo in combos:
            p = ["_"] * NQ
            for q, ch in zip(tg, combo):
                if ch != "I":
                    p[q] = ch
            img = tb[i + 1](stim.PauliString("".join(p)))
            x, z = masks(img, NQ)
            recs.append((f"g{i}:{name} {combo}", (x & 31, z & 31),
                         (x >> FLG) & 1, (z >> ANC) & 1))
    return recs


print("\n" + "=" * 74)
print("Verification cascades, one weight-4 generator each")
print("=" * 74)
summary = {}
for label, bracket in (("no flag", None), ("one flag bracketing the cascade", (0, 4))):
    worst = 0
    surviving = discarded = 0
    for gen in F.OUT_STAB:
        for _, e, flag, _ in verify_round(gen, bracket):
            if flag or any(syndrome(e)):
                discarded += 1
                continue
            surviving += 1
            cls = classify(e)
            if cls not in ("I", "X", "Y", "Z"):
                worst += 1
    summary[label] = {"surviving": surviving, "discarded": discarded, "bad": worst}
    print(f"{label}: {discarded} discarded (flag or syndrome), {surviving} surviving, "
          f"{worst} leaving the code space")
    print(f"   -> {'code space preserved' if worst == 0 else 'NOT safe'}")

# The absorption argument holds only if the Zbar frame bit is recorded AFTER the
# syndrome verification. A logical fault arriving later leaves b5 stale, and a stale
# frame bit is a logical error on the output. This is a protocol ordering requirement.
ZBAR_LAST = True

print("\nORDERING REQUIREMENT: the Zbar frame measurement must come after the g1..g4")
print("verification. A logical fault arriving after b5 is recorded leaves the frame bit")
print("stale, which is a logical error on the output rather than an absorbed one.")

REPORT = [
    ("verify A: measure XXXX and ZZZZ", 8),
    ("prepare B in |0>_L (graph-state synthesis)", n2),
    ("verify B: g1..g4 cascades, weight 4 each", 16),
    ("verify B: one flag per generator", 8),
    ("verify B: Zbar frame measurement", 5),
    ("joint M1, weight 7, r=3", 21),
    ("M1 flag, r=3", 6),
    ("read A out destructively in Z", 0),
]
print("\nCorrected resource count for the teleportation switch:")
for label, k in REPORT:
    print(f"   {label:52s} {k:4d}")
print(f"   {'TOTAL':52s} {sum(k for _, k in REPORT):4d}")
print("   (the earlier figure of 59 did not cost B's verification)")

json.dump({"prep_two_qubit_gates": n2, "prep_method": method,
           "total_two_qubit_gates": sum(k for _, k in REPORT),
           "prep_fault_tally": tally, "verification": summary},
          open("results/prep_factory.json", "w"), indent=2)
print("\nwrote results/prep_factory.json")
