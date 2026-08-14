"""Check every load-bearing quantitative claim in the manuscript against the
verified encoder. Nothing here is asserted; everything is computed.
"""
import itertools
import stim

import frames as F
from frames import ps

U = stim.Tableau.from_circuit(stim.Circuit.from_file("encoder.stim"))
G = [ps(s) for s in F.OUT_STAB]
XBAR, ZBAR = ps(F.OUT_X), ps(F.OUT_Z)


def syndrome(p):
    return tuple(0 if p.commutes(g) else 1 for g in G)


def strip(p):
    q = p.copy()
    q.sign = +1
    return q


STAB_GROUP = set()
for bits in itertools.product([0, 1], repeat=4):
    acc = ps("IIIII")
    for b, g in zip(bits, G):
        if b:
            acc = acc * g
    STAB_GROUP.add(str(strip(acc)))


def classify(p):
    """residual Pauli -> 'I' (stabilizer), 'X', 'Z', 'Y' (logical class)."""
    s = strip(p)
    if str(s) in STAB_GROUP:
        return "I"
    for name, L in (("X", XBAR), ("Z", ZBAR), ("Y", XBAR * ZBAR)):
        if str(strip(s * L)) in STAB_GROUP:
            return name
    return "?"


# standard [[5,1,3]] lookup: perfect code => 15 nonzero syndromes, 15 weight-1 errors
WEIGHT1 = []
for i in range(5):
    for pa in "XYZ":
        WEIGHT1.append(ps("".join(pa if j == i else "I" for j in range(5))))
TABLE = {syndrome(e): e for e in WEIGHT1}
assert len(TABLE) == 15 and (0, 0, 0, 0) not in TABLE


def decode(e):
    s = syndrome(e)
    corr = TABLE.get(s, ps("IIIII"))
    return s, corr, classify(corr * e)


def fmt(p):
    return str(strip(p)).replace("_", "I")


print("=" * 78)
print("A. Paper's hand-typed syndromes (Sec. 5.4.1 and 5.4.2 decoder table)")
print("=" * 78)
claims = [
    ("F1: X on q5 -> syndrome", "IIIIX", (1, 0, 1, 1)),
    ("decoder row X1X5", "XIIIX", (1, 0, 0, 1)),
    ("decoder row X2X5", "IXIIX", (0, 1, 1, 0)),
    ("decoder row X3X5", "IIXIX", (1, 1, 0, 0)),
    ("decoder row X4X5", "IIIXX", (0, 0, 1, 1)),
]
for label, pstr, claimed in claims:
    got = syndrome(ps(pstr))
    print(f"  {label:28s} {pstr}: paper says {claimed}, actual {got}   "
          f"{'OK' if got == claimed else '<-- WRONG'}")

print()
print("  Perfectness check: are the 4 'flagged' syndromes distinct from all 15")
print("  weight-one syndromes, as Sec. 5.4.2 asserts?")
for pstr in ("XIIIX", "IXIIX", "IIXIX", "IIIXX"):
    s = syndrome(ps(pstr))
    print(f"    {pstr} has syndrome {s}, which is ALSO the syndrome of "
          f"{fmt(TABLE[s])} (weight 1)")
print("  => impossible by construction: a perfect code has exactly 15 nonzero")
print("     syndromes and 15 weight-one errors, so every nonzero syndrome")
print("     coincides with a weight-one syndrome. The decoder is disambiguated")
print("     by the FLAG BIT, not by syndrome distinctness.")

print()
print("=" * 78)
print("B. Claim F10: 'Z_i Z_5 is equivalent modulo stabilizers to a weight-1 error'")
print("=" * 78)
for i in (1, 2, 3):
    e = ps("".join("Z" if j in (i - 1, 4) else "I" for j in range(5)))
    s, corr, cls = decode(e)
    print(f"  Z{i}Z5 = {fmt(e)}: syndrome {s}, decoder applies {fmt(corr)}, "
          f"residual class = {cls}   {'correctable' if cls == 'I' else 'LOGICAL ERROR'}")

print()
print("=" * 78)
print("C. Sec. 5.1: 'the re-encoding unitary is weight-preserving for weight-one")
print("   errors by construction' -- residual input errors are correctable later")
print("=" * 78)
bad = 0
print(f"  {'input E':10s} {'U E U+':10s} {'wt':3s} {'syndrome':14s} {'correction':11s} verdict")
for e in WEIGHT1:
    img = U(e)
    s, corr, cls = decode(img)
    wt = sum(1 for c in str(strip(img)) if c not in "I_")
    ok = cls == "I"
    bad += not ok
    print(f"  {fmt(e):10s} {fmt(img):10s} {wt:<3d} {str(s):14s} {fmt(corr):11s} "
          f"{'ok' if ok else 'LOGICAL ' + cls}")
print(f"  => {bad} of {len(WEIGHT1)} weight-one input errors become UNCORRECTABLE "
      f"logical errors")

print()
print("  No-go, independent of U: X1 and X2 on the input block have")
e1, e2 = ps("XIIII"), ps("IXIII")
print(f"    identical input-frame syndromes: "
      f"{[int(not e1.commutes(ps(s))) for s in F.IN_STAB]} == "
      f"{[int(not e2.commutes(ps(s))) for s in F.IN_STAB]}")
print(f"    and differ by X1*X2 = {fmt(e1 * e2)} = the logical X1bar of [[4,2,2]].")
print("    A Clifford is an isomorphism of the Pauli algebra, so their images are")
print("    syndrome-identical and differ by the output logical Xbar under EVERY")
print("    valid U. No downstream decoder can separate them. Residual input errors")
print("    must be caught by Phase 0 post-selection; they can never be corrected.")

print()
print("=" * 78)
print("D. Sec. 4.4 flag gadget: CNOT(q1->f), CNOT(q2->f), CNOT(q4->f)")
print("=" * 78)
flagop = ps("ZZIZI")  # the operator a Z-basis measurement of f reveals, if f starts |0>
print(f"  If f is prepared in |0>, measuring f reveals {fmt(flagop)} on the data.")
print(f"    in the [[5,1,3]] stabilizer group?  {str(strip(flagop)) in STAB_GROUP}")
print(f"    commutes with output Xbar={F.OUT_X}? {flagop.commutes(XBAR)}")
print(f"    commutes with output Zbar={F.OUT_Z}? {flagop.commutes(ZBAR)}")
inframe = set()
for bits in itertools.product([0, 1], repeat=4):
    acc = ps("IIIII")
    for b, g in zip(bits, [ps(s) for s in F.IN_STAB]):
        if b:
            acc = acc * g
    inframe.add(str(strip(acc)))
print(f"    in the input-frame stabilizer group? {str(strip(flagop)) in inframe}")
print(f"    commutes with input stabilizer XXXXI? {flagop.commutes(ps('XXXXI'))}")
print("  => wherever it is placed, it is a measurement of a non-stabilizer operator")
print("     that anticommutes with a logical (output) or a stabilizer (input).")
print("     As written this is a destructive parity measurement, not a flag.")
print()
print("  Sec. 5.4.1 F13 instead describes f prepared in |+> ('H-CNOT-H sandwich').")
print("  CNOT(c->t) = |0><0|_c (x) I + |1><1|_c (x) X_t, and X|+> = |+>, so with the")
print("  flag as TARGET in |+> the gadget is exactly the identity: f is deterministic")
print("  and flags nothing. Both readings of Sec. 4.4/5.4.1 are broken, differently.")

print()
print("=" * 78)
print("E. Two-qubit gate count, exact")
print("=" * 78)
enc = stim.Circuit.from_file("encoder.stim")
n_enc = sum(len(i.targets_copy()) // 2 for i in enc.flattened() if i.name == "CX")
r = 3
rows = [
    ("Phase 0: measure XXXX and ZZZZ", 4 + 4),
    ("Phase 1: ancilla verification", 1),
    ("Phase 2: measure Z2bar = ZZII (controls q1,q2)", 2),
    ("Phase 3: verified re-encoder (this repo, unoptimized)", n_enc),
    ("Phase 3: flag coupling as described", 3),
    (f"Phase 4: 4 generators of weight 4, r={r} rounds", 4 * 4 * r),
]
tot = 0
for label, n in rows:
    tot += n
    print(f"  {label:56s} {n:4d}")
print(f"  {'TOTAL':56s} {tot:4d}")
print(f"  Manuscript claims 'approximately 15 CNOT gates' (abstract, Sec. 8, Table 3).")
print(f"  Phase 4 alone at r=3 needs {4*4*r}.")
