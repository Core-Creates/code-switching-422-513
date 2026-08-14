"""Every load-bearing quantitative claim in code_switching_paper.docx, checked against
the verified encoder. Test ids carry the manuscript's claim; assertions carry the
computed truth. Numbering matches the defect table in FINDINGS.md."""
import itertools

import pytest
import stim

import frames as F
import flagsearch as FS
from frames import ps

G = [ps(s) for s in F.OUT_STAB]
XBAR, ZBAR = ps(F.OUT_X), ps(F.OUT_Z)


def syndrome(p):
    return tuple(0 if p.commutes(g) else 1 for g in G)


def strip(p):
    q = p.copy()
    q.sign = +1
    return q


def group_of(gens):
    out = set()
    for bits in itertools.product([0, 1], repeat=len(gens)):
        acc = ps("IIIII")
        for b, g in zip(bits, gens):
            if b:
                acc = acc * g
        out.add(str(strip(acc)))
    return out


STAB_GROUP = group_of(G)
IN_GROUP = group_of([ps(s) for s in F.IN_STAB])
WEIGHT1 = [ps("".join(p if j == i else "I" for j in range(5)))
           for i in range(5) for p in "XYZ"]
TABLE = {syndrome(e): e for e in WEIGHT1}


def classify(p):
    s = strip(p)
    if str(s) in STAB_GROUP:
        return "I"
    for name, L in (("X", XBAR), ("Z", ZBAR), ("Y", XBAR * ZBAR)):
        if str(strip(s * L)) in STAB_GROUP:
            return name
    return "?"


# ---------------------------------------------------------------- defect 2
def test_defect2_paper_gate_list_does_not_switch_codes():
    """Sec. 3.3: U = (I x S5).CX(q5->q4).CX(q5->q1).CZ(q1,q5).CX(q3->q5)
    .CX(q1->q5).CX(q2->q5).H5, applied right to left."""
    c = stim.Circuit()
    c.append("H", [4])
    c.append("CX", [1, 4, 0, 4, 2, 4])
    c.append("CZ", [0, 4])
    c.append("CX", [4, 0, 4, 3])
    c.append("S", [4])
    Up = stim.Tableau.from_circuit(c)
    pairs = list(zip(F.IN_STAB, F.OUT_STAB)) + [(F.IN_X, F.OUT_X), (F.IN_Z, F.OUT_Z)]
    correct = sum(1 for a, b in pairs if Up(ps(a)) == ps(b))
    assert correct == 0, "expected the manuscript's gate list to map nothing correctly"
    images = [str(strip(Up(ps(s)))) for s in F.IN_STAB]
    assert not all(i in STAB_GROUP for i in images), \
        "stabilizer images are not even in the [[5,1,3]] stabilizer group"


def test_sec33_codeword_expansion_is_correct():
    """The one hand-typed object in Sec. 3.3 that checks out."""
    import functools
    import numpy as np
    terms = ("00000 10010 01001 10100 01010 11011 00110 11000 11101 00011 11110 "
             "01111 10001 01100 10111 00101").split()
    signs = [1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1]
    v = np.zeros(32, dtype=complex)
    for t, s in zip(terms, signs):
        v[sum(int(b) << (4 - k) for k, b in enumerate(t))] += s / 4
    m = {"I": np.eye(2), "X": np.array([[0, 1], [1, 0]]),
         "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.array([[1, 0], [0, -1]])}
    assert abs(np.linalg.norm(v) - 1) < 1e-12
    for s in F.OUT_STAB + [F.OUT_Z]:
        M = functools.reduce(np.kron, [m[c] for c in s])
        assert abs(np.real(np.vdot(v, M @ v)) - 1) < 1e-12


# ---------------------------------------------------------------- defect 3, 4
def test_defect3_flag_gadget_is_a_destructive_measurement():
    """Sec. 4.4: CNOT(q1->f), CNOT(q2->f), CNOT(q4->f) with f in |0> measures ZZIZI."""
    flagop = ps("ZZIZI")
    assert str(strip(flagop)) not in STAB_GROUP
    assert not flagop.commutes(XBAR), "anticommutes with the output logical Xbar"
    assert str(strip(flagop)) not in IN_GROUP
    assert not flagop.commutes(ps("XXXXI")), "anticommutes with the input stabilizer"


def test_defect3_flag_gadget_with_plus_prep_is_identity():
    """Sec. 5.4.1 F13 implies f in |+>. CNOT with the target in |+> is the identity,
    so the flag is deterministic and flags nothing."""
    c = stim.Circuit()
    c.append("I", range(6))
    c.append("CX", [0, 5, 1, 5, 3, 5])
    T = stim.Tableau.from_circuit(c)
    xf = stim.PauliString(6)
    xf[5] = 1
    assert T(xf) == xf, "X on the flag is preserved, so a |+> flag never fires"


def test_defect4_phase1_verification_is_a_noop():
    """Sec. 4.2: a3 in |+> as the CNOT target cannot detect an X error on q5."""
    c = stim.Circuit()
    c.append("I", range(2))
    c.append("CX", [0, 1])
    T = stim.Tableau.from_circuit(c)
    xa = stim.PauliString(2)
    xa[1] = 1
    assert T(xa) == xa, "the verification ancilla is untouched, so it always reads 0"


# ---------------------------------------------------------------- defect 6
@pytest.mark.parametrize("pstr,paper_claim,truth", [
    ("IIIIX", (1, 0, 1, 1), (0, 0, 1, 1)),   # F1
    ("XIIIX", (1, 0, 0, 1), (0, 0, 1, 0)),   # decoder row X1X5
    ("IXIIX", (0, 1, 1, 0), (1, 0, 1, 1)),   # decoder row X2X5
    ("IIXIX", (1, 1, 0, 0), (1, 1, 1, 1)),   # decoder row X3X5
    ("IIIXX", (0, 0, 1, 1), (0, 1, 0, 1)),   # decoder row X4X5
])
def test_defect6_hand_typed_syndromes(pstr, paper_claim, truth):
    got = syndrome(ps(pstr))
    assert got == truth
    assert got != paper_claim


# ---------------------------------------------------------------- defect 7
def test_defect7_perfect_code_forbids_distinct_flagged_syndromes():
    """Sec. 5.4.2 claims the flagged syndromes are distinct from all 15 weight-one
    syndromes. A perfect code has exactly 15 nonzero syndromes and 15 weight-one
    errors, so no nonzero syndrome can be distinct from all of them."""
    assert len(TABLE) == 15 and (0, 0, 0, 0) not in TABLE
    for pstr in ("XIIIX", "IXIIX", "IIXIX", "IIIXX"):
        s = syndrome(ps(pstr))
        assert s in TABLE, "every nonzero syndrome collides with a weight-one error"


# ---------------------------------------------------------------- defect 8
@pytest.mark.parametrize("i,expected_class", [(1, "Y"), (2, "X"), (3, "X")])
def test_defect8_ZiZ5_is_not_stabilizer_equivalent_to_weight_one(i, expected_class):
    e = ps("".join("Z" if j in (i - 1, 4) else "I" for j in range(5)))
    corr = TABLE.get(syndrome(e), ps("IIIII"))
    assert classify(corr * e) == expected_class != "I"


# ---------------------------------------------------------------- defect 5, Lemma 1
def test_lemma1_input_errors_are_confusable():
    """12 of 15 weight-one input errors lie in a confusable pair, so no encoder and no
    decoder can correct them. This is Knill-Laflamme on the input frame alone."""
    S = [ps(s) for s in F.IN_STAB]

    def in_syn(p):
        return tuple(0 if p.commutes(g) else 1 for g in S)

    cls = {}
    for e in WEIGHT1:
        cls.setdefault(in_syn(e), []).append(e)
    bad = set()
    for _, es in cls.items():
        for a, b in itertools.combinations(es, 2):
            if str(strip(a * b)) not in IN_GROUP:
                bad.add(str(strip(a)))
                bad.add(str(strip(b)))
    assert len(bad) == 12
    # the 3 survivors are exactly the errors on the fresh q5
    survivors = {str(strip(e)) for e in WEIGHT1} - bad
    assert survivors == {str(strip(ps(p))) for p in ("IIIIX", "IIIIY", "IIIIZ")}


def test_lemma1_three_survivors_are_correctable_by_a_synthesized_decoder(U):
    imgs = {n: U(ps(p)) for n, p in
            [("X5", "IIIIX"), ("Y5", "IIIIY"), ("Z5", "IIIIZ")]}
    assert str(strip(imgs["Z5"])) in STAB_GROUP, "Z on the fresh ancilla is harmless"
    assert str(strip(imgs["X5"] * imgs["Y5"])) in STAB_GROUP, \
        "X5 and Y5 images differ by a stabilizer, so one correction handles both"
    assert syndrome(imgs["X5"]) == syndrome(imgs["Y5"]) != (0, 0, 0, 0)
    # the standard weight-one table gets them wrong, which is why Sec. 5.1 fails
    corr = TABLE[syndrome(imgs["X5"])]
    assert classify(corr * imgs["X5"]) != "I"


def test_lemma1_holds_for_every_encoder():
    """X1 and X2 share an input syndrome and differ by the logical X1bar. A Clifford is
    an isomorphism of the Pauli algebra, so this survives any U."""
    S = [ps(s) for s in F.IN_STAB]
    e1, e2 = ps("XIIII"), ps("IXIII")
    assert [e1.commutes(s) for s in S] == [e2.commutes(s) for s in S]
    assert str(strip(e1 * e2)) == str(strip(ps("XXIII"))) == str(strip(ps(F.IN_X)))


# ---------------------------------------------------------------- defect 11
def test_defect11_exact_two_qubit_gate_count(enc):
    """Abstract and Sec. 8 say 'approximately 15 CNOT gates' for the whole protocol."""
    r = 3
    budget = {
        "phase0 measure XXXX and ZZZZ": 4 + 4,
        "phase1 ancilla verification": 1,
        "phase2 measure Z2bar": 2,
        "phase3 verified re-encoder": enc.ncx,
        "phase3 flag coupling as described": 3,
        f"phase4 four weight-4 generators, r={r}": 4 * 4 * r,
    }
    assert enc.ncx == 17
    assert budget[f"phase4 four weight-4 generators, r={r}"] == 48
    assert sum(budget.values()) == 79
    assert sum(budget.values()) > 5 * 15
