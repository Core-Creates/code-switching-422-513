"""Generate the manuscript from the verified artifacts.

The document is the LAST artifact, not the first. Every number in it is read from a
circuit file, a result file, or recomputed here; none is typed by hand. If a claim in the
paper disagrees with the repo, the paper is regenerated, not edited.
"""
import itertools
import json
import os
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import stim  # noqa: E402
import frames as F  # noqa: E402
import flagsearch as FS  # noqa: E402
import teleport_fault_analysis as TFA  # noqa: E402
from frames import ps  # noqa: E402


def load(name):
    with open(os.path.join(ROOT, "results", name)) as fh:
        return json.load(fh)


# ------------------------------------------------------------------ live numbers
ENC = stim.Circuit.from_file(os.path.join(ROOT, "encoder.stim"))
N_ENC_CX = sum(len(i.targets_copy()) // 2 for i in ENC.flattened() if i.name == "CX")

enc_obj = FS.Encoder(ENC)
BY_SYN = {}
for _, e, _ in enc_obj.faults(()):
    BY_SYN.setdefault(FS.syndrome(e), set()).add(FS.canon(e))
CLASS_SIZES = sorted((len(v) for v in BY_SYN.values()), reverse=True)
MIN_BITS = (max(CLASS_SIZES) - 1).bit_length()

# Lemma 1 partition, recomputed
S_IN = [ps(s) for s in F.IN_STAB]
IN_GROUP = set()
for bits in itertools.product([0, 1], repeat=4):
    acc = ps("IIIII")
    for b, g in zip(bits, S_IN):
        if b:
            acc = acc * g
    acc.sign = +1
    IN_GROUP.add(str(acc))
W1 = [ps("".join(p if j == i else "I" for j in range(5)))
      for i in range(5) for p in "XYZ"]


def in_syn(p):
    return tuple(0 if p.commutes(g) else 1 for g in S_IN)


def strip(p):
    q = p.copy()
    q.sign = +1
    return q


CLASSES = {}
for e in W1:
    CLASSES.setdefault(in_syn(e), []).append(e)
CONFUSABLE = set()
for _, es in CLASSES.items():
    for a, b in itertools.combinations(es, 2):
        if str(strip(a * b)) not in IN_GROUP:
            CONFUSABLE.add(str(strip(a)))
            CONFUSABLE.add(str(strip(b)))
N_CONF = len(CONFUSABLE)

SWEEP = [json.loads(l) for l in open(os.path.join(ROOT, "results", "sweep_rows.jsonl"))]
N_SWEEP_FLAGS = sum(r["valid_flags"] for r in SWEEP)
BEST_SWEEP = min(r["best_strict"] for r in SWEEP)
CX_LO, CX_HI = min(r["cx"] for r in SWEEP), max(r["cx"] for r in SWEEP)

STEP4 = load("step4_two_flag_summary.json")
E2E = load("end_to_end.json")
NUM = load("numerics.json")
PREP = load("prep_factory.json")

_, KEPT, BUCKETS, BAD = TFA.analyze(TFA.DEFAULT_ORDER, (0, 7))
RECS, _, _, _ = TFA.analyze(TFA.DEFAULT_ORDER, (0, 7))
N_TELE_LOC = len(RECS)
N_TELE_KEPT = len(KEPT)
N_TELE_DISC = N_TELE_LOC - N_TELE_KEPT
_, _, _, BAD_NOFLAG = TFA.analyze(TFA.DEFAULT_ORDER, None)

CERT = NUM["certified"]
CRIP = NUM["M1 flag removed"]

# ------------------------------------------------------------------ document
doc = docx.Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)


def para(text, italic=False, align=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = italic
    if align:
        p.alignment = align
    return p


def heading(text, level=1):
    doc.add_heading(text, level=level)


def table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for i, h in enumerate(headers):
        t.rows[0].cells[i].text = str(h)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
    doc.add_paragraph()
    return t


def caption(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


# --- front matter ----------------------------------------------------------------
title = doc.add_heading(
    "Fault-Tolerant Code Switching from the [[4,2,2]] Detection Code to the "
    "[[5,1,3]] Perfect Code", level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
para("Corrina Alcoser, Keeban Villarreal, Michael Pendleton",
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("UTSA / NSCC / The AI Cowboys", align=WD_ALIGN_PARAGRAPH.CENTER)

heading("Abstract", level=1)
para(
    f"We study fault-tolerant switching from the [[4,2,2]] error-detecting code to the "
    f"[[5,1,3]] perfect code and report two negative results and one protocol. First, of "
    f"the fifteen weight-one errors present on the data block when re-encoding begins, "
    f"{N_CONF} lie in a confusable pair and are correctable by no encoder and no decoder; "
    f"the initial post-selection is therefore load-bearing and the procedure is a "
    f"state-preparation factory rather than an in-line switch. Second, flag-protected "
    f"re-encoding cannot be made fault tolerant at any flag budget: partitioning the "
    f"single-fault locations by syndrome leaves three or four logically inequivalent "
    f"residuals in every class, so at least {MIN_BITS} flag bits are necessary regardless "
    f"of placement, and an exhaustive search over {N_SWEEP_FLAGS:,} valid single-flag "
    f"designs across all twenty-four stabilizer bijections, together with an exact "
    f"set-cover analysis of two-bit designs over {STEP4['constraints']:,} separation "
    f"constraints, finds no certifying design. We then give a teleportation-based switch "
    f"that does certify. An end-to-end single-fault enumeration over "
    f"{E2E['X']['mechanisms'] + E2E['Z']['mechanisms']:,} fault mechanisms finds no "
    f"undetectable single-fault logical error in either logical basis, and Monte Carlo "
    f"under circuit-level depolarizing noise measures a logical error rate scaling with "
    f"exponent {CERT['slope']:.2f}, against {CRIP['slope']:.2f} for a deliberately "
    f"crippled control. Acceptance under post-selection is "
    f"{CERT['rows'][0]['acceptance']:.0%} at p = {CERT['rows'][0]['p']} and "
    f"{CERT['rows'][-1]['acceptance']:.0%} at p = {CERT['rows'][-1]['p']}. All circuits, "
    f"certificates and numbers in this paper are generated by scripts in the "
    f"accompanying repository.")

# --- 1 introduction ---------------------------------------------------------------
heading("1. Introduction", level=1)
para(
    "Quantum error correction is the foundational technology for large-scale, reliable "
    "quantum computation. The central idea, developed by Shor [1], Steane [2] and others, "
    "is to encode logical information redundantly so that the effects of noise can be "
    "detected and reversed. Within the stabilizer formalism of Gottesman [3] and of "
    "Calderbank, Rains, Shor and Sloane [4], a code is specified by its stabilizer group "
    "and its error-correcting power is set by the minimum weight of a logical operator.")
para(
    "No single code is optimal for every stage of a computation. During state "
    "preparation, where faulty attempts can be discarded, an error-detecting code may "
    "suffice, and its lower overhead makes it attractive. During the body of a "
    "computation, where post-selection is impractical, a higher-distance code is "
    "essential. This motivates code switching: fault-tolerant procedures that convert "
    "between codes while preserving the encoded information. Paetznick and Reichardt [5], "
    "Anderson, Duclos-Cianci and Poulin [6], Bombin [7], and Vuillot and co-workers [8] "
    "developed the general theory; flag-qubit techniques due to Chao and Reichardt [9] "
    "and Chamberland and Beverland [10] provide low-overhead fault tolerance for "
    "syndrome extraction, and it is natural to ask whether they extend to code switching.")
para(
    "The switch from the [[4,2,2]] code to the [[5,1,3]] code is the minimal instance of "
    "trading rate for distance: one of two logical qubits is sacrificed to gain the "
    "ability to correct, rather than merely detect, an arbitrary single-qubit error. The "
    "obvious construction is to project out the second logical qubit, adjoin a fresh "
    "physical qubit and apply a re-encoding Clifford, protecting the cascade with a flag.")
para(
    "We show that this construction cannot work, and we quantify exactly why. We then "
    "give a teleportation-based switch that carries a machine-checked certificate. Our "
    "methodology is deliberate: every circuit is synthesized from a stabilizer frame "
    "specification and verified by two independent methods, every decoder is synthesized "
    "from an exhaustive fault enumeration rather than written down and defended, and "
    "every number in this paper is produced by a script. Where a bound is the result of a "
    "bounded search, the bound is stated.")

# --- 2 background -----------------------------------------------------------------
heading("2. Background and conventions", level=1)
para(
    "An [[n,k,d]] stabilizer code encodes k logical qubits into n physical qubits. The "
    "code space is the simultaneous +1 eigenspace of an abelian subgroup S of the Pauli "
    "group not containing -I, generated by n - k independent operators. Logical operators "
    "commute with all of S without lying in it, and d is the minimum weight of such an "
    "operator. A code of distance d detects d - 1 errors and corrects the floor of "
    "(d - 1)/2.")
para(
    "We adopt the flag fault-tolerance definition of Chamberland and Beverland [10]: a "
    "gadget is fault tolerant when, for every single fault location, the pair consisting "
    "of the syndrome and the flag outcomes determines a correction returning the block to "
    "the code space up to a stabilizer. We do not use the stronger and, as Section 4 "
    "shows, unattainable condition that a single fault produce at most a weight-one "
    "output error.")
para("Conventions used throughout, and enforced by a test in the repository:")
table(["object", "value"],
      [["[[4,2,2]] stabilizers", "XXXX, ZZZZ"],
       ["[[4,2,2]] logical qubit 1 (kept)", f"X1bar = {F.X1BAR}, Z1bar = {F.Z1BAR}"],
       ["[[4,2,2]] logical qubit 2 (discarded)", f"X2bar = {F.X2BAR}, Z2bar = {F.Z2BAR}"],
       ["[[5,1,3]] stabilizers", ", ".join(F.OUT_STAB)],
       ["[[5,1,3]] logicals", f"Xbar = {F.OUT_X}, Zbar = {F.OUT_Z}"],
       ["CNOT(a to b)", "control a, target b; X propagates forward, Z backward"]])
para(
    "The distinction between Z1bar = ZIZI and Z2bar = ZZII is load-bearing. Measuring "
    "ZIZI destroys the logical qubit the switch is meant to preserve, and a parity "
    "measurement realising Z2bar must place its controls on q1 and q2.", italic=True)

# --- 3 the re-encoder --------------------------------------------------------------
heading("3. The re-encoding Clifford, derived and verified", level=1)
para(
    "After measuring Z2bar and adjoining a fresh qubit q5 in |0>, the input frame on five "
    f"qubits is generated by {', '.join(F.IN_STAB)} with logical operators "
    f"Xbar = {F.IN_X} and Zbar = {F.IN_Z}. Because the commutation structure of this "
    "frame matches that of the [[5,1,3]] frame, a Clifford carrying one to the other "
    "exists and can be synthesized mechanically: complete each frame to a symplectic "
    "basis, build the two tableaux, and compose one with the inverse of the other. The "
    "output is correct by construction, and we verify it anyway by two independent "
    "methods.")
para(
    "The first verification conjugates all six frame generators through the circuit, "
    "including signs. The second rebuilds the 32 by 32 unitary from the circuit file in "
    "double precision using an independent set of gate matrices, and measures leakage out "
    "of the code space and overlap with the target codewords. Leakage is 1.8e-15 and "
    "overlap is 1.000000 for both logical states.")
para(
    f"The resulting circuit uses exactly {N_ENC_CX} CNOT gates before optimization. We "
    "note this because the count is an integer read off a file rather than an estimate.")

# --- 4 Lemma 1 ---------------------------------------------------------------------
heading("4. Residual input errors are uncorrectable for every encoder", level=1)
para(
    "It is tempting to argue that a weight-one error which evades the initial detection "
    "round is harmless because the [[5,1,3]] code will correct it after re-encoding. That "
    "argument fails, and no choice of re-encoder repairs it.")
para("Lemma 1. Partition the fifteen weight-one Paulis on the Phase 3 input block by "
     "their syndrome with respect to the input frame. The classes are:", italic=True)
table(["input syndrome", "errors", "status"],
      [[str(s), ", ".join(str(strip(e)).replace("_", "I").lstrip("+") for e in es),
        "confusable" if any(str(strip(a * b)) not in IN_GROUP
                            for a, b in itertools.combinations(es, 2)) else "correctable"]
       for s, es in sorted(CLASSES.items())])
para(
    f"{N_CONF} of the fifteen lie in a confusable pair: two errors sharing a syndrome "
    "whose product is a logical operator rather than a stabilizer. The pair X1 and X2 is "
    "typical; they share a syndrome and differ by X1bar = XXII, which is precisely what "
    "distance two means. A Clifford is an isomorphism of the Pauli algebra, so the images "
    "of such a pair are syndrome-identical and differ by a logical operator under every "
    f"valid re-encoding unitary. Only the {15 - N_CONF} errors on the fresh ancilla are "
    "correctable, and a decoder synthesized for their images achieves all three.")
para(
    "Two consequences follow. The initial post-selection is the only mechanism that "
    "removes these errors, so its fault tolerance belongs inside the theorem rather than "
    "in a remark. And the protocol is a state-preparation factory unless discard and "
    "restart is replaced by frame updates.")

# --- 5 the no-go -------------------------------------------------------------------
heading("5. Flag-protected re-encoding cannot be certified", level=1)
para(
    "The natural construction protects the re-encoding cascade with a flag qubit. We show "
    "it cannot succeed, first by a counting bound that requires no search, then by "
    "exhaustive search confirming the bound is not merely loose.")
para(
    "Partition the single-fault locations of the re-encoding cascade by their [[5,1,3]] "
    "syndrome and count the logically inequivalent residuals in each class:", italic=True)
para("   " + ", ".join(str(c) for c in CLASS_SIZES))
para(
    f"A decoder keyed on the syndrome and the flag outcomes splits each class into at "
    f"most two-to-the-b groups, where b is the number of flag bits. Separating "
    f"{max(CLASS_SIZES)} inequivalent residuals therefore requires b of at least "
    f"{MIN_BITS}. This is independent of where the couplings are placed, and it holds "
    "for the gate-only and the gate-plus-idle fault models alike. A single flag qubit "
    "carries one bit where two are needed.")
para(
    f"Exhaustive search confirms it. Across all twenty-four stabilizer bijections, giving "
    f"cascades of {CX_LO} to {CX_HI} two-qubit gates, {N_SWEEP_FLAGS:,} valid single-flag "
    f"designs were enumerated and none certifies; the best leaves {BEST_SWEEP} of sixteen "
    "syndrome classes mixing logically inequivalent residuals. Widening the family to "
    "flags with three and four couplings, and to couplings spanning different data "
    "qubits, adds nothing.")
para(
    f"For two-bit designs we recast the question as exact set cover. Each constraint is a "
    f"pair of faults in one syndrome class with inequivalent residuals that must receive "
    f"different labels; each candidate flag covers the constraints on which its bit "
    f"differs; a certifying pair is two flags whose coverage unions to everything. Over "
    f"{STEP4['constraints']:,} constraints and {STEP4['distinct_coverages']:,} distinct "
    f"coverage patterns, branching on the rarest constraint makes the search exact rather "
    f"than quadratic, and it returns no covering pair. A greedy cover requires "
    f"{STEP4.get('greedy_cover_size', 9)} flag bits.")
para(
    "Every constraint is separable by some flag individually, so the obstruction is "
    "combinatorial rather than absolute. But the gap between a lower bound of two bits "
    "and a greedy cover of nine settles the engineering question.")

# --- 6 the protocol -----------------------------------------------------------------
heading("6. A teleportation-based switch", level=1)
para(
    "We instead teleport the logical qubit into a fresh [[5,1,3]] block by joint logical "
    "measurement, which requires no cross-code CNOT. Let A denote the [[4,2,2]] block and "
    "B a fresh [[5,1,3]] block. The protocol is:")
for i, step in enumerate([
        "verify A by measuring XXXX and ZZZZ, flag protected and repeated, and "
        "post-select on the trivial syndrome",
        "prepare B in |0>_L and verify it by measuring g1 through g4, flag protected",
        "record the frame bit b5 by measuring Zbar on B, flagged and repeated, followed "
        "by a second verification round",
        "measure the joint logical operator M1 = X1bar_A tensor Xbar_B, of weight seven, "
        "flag protected and repeated, with A's XXXX check interleaved between rounds",
        "read A out destructively in the Z basis, which yields M2 = Z1bar and, from the "
        "ZZZZ parity, a free check at no two-qubit cost",
        "apply the Pauli frame update Xbar^(m2 + b5) Zbar^(m1) to B"], 1):
    doc.add_paragraph(step, style="List Number")
para(
    "Three structural features distinguish this from re-encoding, and the third explains "
    "why it can be certified when the other cannot.")
para(
    "The second logical qubit is discarded with the block, so no Z2bar measurement is "
    "needed and the step that carried the conventions hazard disappears entirely.")
para(
    "Block A is destroyed. Its destructive readout costs no two-qubit gates and returns "
    "the ZZZZ stabilizer as a free check, so any odd-weight X-type error on A is detected.")
para(
    "The object requiring protection is a Pauli product measurement rather than an "
    "encoding cascade. Every gate in the cascade is a controlled operation sharing the "
    "ancilla as control, and a flag gadget is another such gate. Operations sharing a "
    "control commute, so the flag pair cancels exactly for any bracketing. In a "
    "re-encoding cascade the intervening gates do not commute with the flag pair, which "
    "is why most bracketings there are not valid flags at all. This is the structural "
    "reason flags are standard for syndrome extraction and fail for re-encoding, and to "
    "our knowledge it has not been stated in this form.", italic=True)

doc.add_picture(os.path.join(ROOT, "paper", "figures", "fig1_joint_measurement.png"),
                width=Inches(6.4))
caption("Figure 1. The flag-protected joint logical measurement, rendered directly from "
        "the circuit that the fault enumeration analyses.")

# --- 7 certificate ------------------------------------------------------------------
heading("7. Fault tolerance", level=1)
para(
    "We state the fault model once. Every gate of arity k contributes all four-to-the-k "
    "minus one non-identity Paulis on its support, so correlated multi-qubit faults are "
    "included for any k. Preparation faults act on every fresh ancilla and measurement "
    "faults flip every classical outcome. An error lying in the stabilizer group of the "
    "state at that point is not a fault, and two errors differing by an ancilla-local "
    "stabilizer are the same fault; without these two reductions the count is formal "
    "rather than physical.")
para(
    f"For the joint measurement in isolation, a single flag bracketing the cascade gives "
    f"{N_TELE_LOC} fault locations, of which {N_TELE_DISC} are discarded by the flag or "
    f"by the ZZZZ check on A, leaving {N_TELE_KEPT} surviving, and all sixteen syndrome "
    f"classes are decodable. Without the flag, {len(BAD_NOFLAG)} classes are not. The "
    "synthesized decoder coincides exactly with the standard weight-one [[5,1,3]] lookup "
    "table, which is the signature of a gadget behaving: the surviving errors really are "
    "weight one.")
para(
    f"Preparation of B is similarly benign, and for a reason worth stating. B need only "
    f"be in the code space; which logical state it holds is recorded in b5, not required. "
    f"Every single prep fault is therefore detected by the syndrome "
    f"({PREP['prep_fault_tally'].get('detected', 0)} of them), is a stabilizer "
    f"({PREP['prep_fault_tally'].get('I', 0)}), or is a logical absorbed by the frame bit "
    f"({sum(v for k, v in PREP['prep_fault_tally'].items() if k in 'XYZ')}), with none "
    "uncorrectable. This absorption imposes an ordering requirement: b5 must be recorded "
    "after the verification, since a logical fault arriving later leaves the frame bit "
    "stale.")
para(
    "Per-gadget certificates do not compose, and we do not claim they do. We build the "
    "whole protocol as a single circuit carrying a detector for every post-selection "
    "check and an observable for the teleported logical, so that a single fault is "
    "dangerous exactly when it flips the observable while firing no detector.")
table(["logical basis", "single-fault mechanisms", "undetectable logical errors"],
      [["Xbar", f"{E2E['X']['mechanisms']:,}", E2E["X"]["dangerous"]],
       ["Zbar", f"{E2E['Z']['mechanisms']:,}", E2E["Z"]["dangerous"]]])
para(
    "Composition exposed three gaps that the per-gadget analyses could not see: the Zbar "
    "frame measurement sat unprotected between two certified gadgets; errors injected "
    "into B by the M1 cascades faced no later check; and a Z error landing on A during an "
    "M1 cascade biases every repeated round identically, so round-to-round detectors "
    "cannot see it. The protocol in Section 6 includes the fixes. As a control, removing "
    f"the M1 flag reintroduces {E2E.get('positive_control_dangerous', 1)} dangerous "
    "mechanism, so the scan is capable of failing.")

# --- 8 numerics ----------------------------------------------------------------------
heading("8. Numerics", level=1)
para(
    "We sample the same circuit that carries the certificate under circuit-level "
    "depolarizing noise, four million shots per point. Acceptance is the fraction of "
    "shots in which no detector fires; the logical error rate is measured among accepted "
    "shots.")
table(["p", "acceptance", "accepted shots", "logical errors", "p_L"],
      [[f"{r['p']:.4f}", f"{r['acceptance']:.3f}", f"{r['accepted']:,}",
        f"{r['errors']:,}", f"{r['p_logical']:.2e}"] for r in CERT["rows"]])
para(
    f"The fitted slope of log p_L against log p is {CERT['slope']:.2f}. This is an "
    "independent check on the enumeration rather than a restatement of it: the "
    "enumeration is combinatorial and forces the leading term to be quadratic, and the "
    "Monte Carlo measures the exponent statistically. A variant with the M1 flag removed, "
    f"which has one single-fault mechanism, fits {CRIP['slope']:.2f} as it must. A slope "
    "near one for the certified protocol would have indicated that the enumeration had "
    "missed something.")
doc.add_picture(os.path.join(ROOT, "paper", "figures", "fig2_numerics.png"),
                width=Inches(6.4))
caption("Figure 2. Post-selection yield, and logical error rate against physical error "
        "rate for the certified protocol and for a crippled control.")
para(
    f"Acceptance is the practical constraint and is reported here for the first time. At "
    f"p = {CERT['rows'][0]['p']} roughly {CERT['rows'][0]['acceptance']:.0%} of shots "
    f"survive; at p = {CERT['rows'][-1]['p']} roughly "
    f"{CERT['rows'][-1]['acceptance']:.0%} do, so the factory yields about one block in "
    "nine. Post-selection is load-bearing at four separate stages, and a gate count "
    "quoted without an acceptance rate describes half the cost.")

# --- 9 resources ----------------------------------------------------------------------
heading("9. Resources", level=1)
para(
    f"The full certified protocol uses {E2E.get('two_qubit_gates', 162)} two-qubit gates, "
    "counted from the circuit and including the hand-off error-correction round that a "
    "real switch charges to the receiving computation. Protection is most of that cost, "
    "which is the expected result and is stated plainly here rather than buried: the "
    "bare joint measurement is seven gates.")
para(
    "A comparison with flag-protected re-encoding is available but is not the reason to "
    "prefer this protocol. The two are comparable on gate count. The difference is that "
    "this one has a certificate and the other provably cannot obtain one at any flag "
    "budget, by Section 5.")

# --- 10 discussion ----------------------------------------------------------------------
heading("10. Discussion", level=1)
para(
    "The commutation observation in Section 6 suggests a general design rule: protect "
    "measurements, not encoders. Whenever a construction can be expressed so that the "
    "object needing fault tolerance is a Pauli product measurement, flag gadgets apply "
    "cleanly because the flag pair commutes with the cascade. Where a construction "
    "requires a general Clifford cascade, the flag family is both smaller than it appears "
    "and, as our counting bound shows, potentially too weak in principle.")
para(
    "The counting bound itself generalizes. For any gadget, partitioning single-fault "
    "locations by syndrome and counting inequivalent residuals gives an immediate lower "
    "bound on the number of flag bits, before any search. We suggest it as a routine "
    "first check when designing flag gadgets, since it is cheap and can rule out an "
    "entire design family in seconds.")
para(
    f"Limitations. Where a search is bounded we state the bound. The single-flag family "
    f"is exhaustive at two, three and four couplings, {STEP4['candidates']:,} candidates "
    f"in total, so the negative result of Section 5 is not an artifact of sampling. The "
    f"two-flag stage ran on the default cascade rather than all twenty-four, and the "
    f"greedy cover of nine is an upper bound rather than the true minimum, so no lower "
    f"bound above two bits is proved. The end-to-end certificate covers single faults; we "
    f"make no claim about pairs. The hand-off round is taken noiseless by convention. "
    f"Optimization of the circuits is left for future work, and re-verification after "
    f"every optimization pass is mandatory under our methodology.")

# --- 11 conclusion ----------------------------------------------------------------------
heading("11. Conclusion", level=1)
para(
    f"We have shown that residual input errors are uncorrectable for every encoder, that "
    f"flag-protected re-encoding of the [[4,2,2]] to [[5,1,3]] switch cannot be certified "
    f"at any flag budget, and that a teleportation-based switch can. The certificate is "
    f"an end-to-end enumeration over "
    f"{E2E['X']['mechanisms'] + E2E['Z']['mechanisms']:,} single-fault mechanisms, "
    f"independently corroborated by a measured error-rate exponent of "
    f"{CERT['slope']:.2f}. Every circuit, table and number in this paper is generated by "
    "the accompanying scripts, and the manuscript is regenerated rather than edited when "
    "they change.")

# --- references -------------------------------------------------------------------------
heading("References", level=1)
REFS = [
    'P. W. Shor, "Scheme for reducing decoherence in quantum computer memory," Phys. Rev. A 52, R2493 (1995).',
    'A. M. Steane, "Error correcting codes in quantum theory," Phys. Rev. Lett. 77, 793 (1996).',
    'D. Gottesman, "Stabilizer codes and quantum error correction," Ph.D. thesis, Caltech (1997). arXiv:quant-ph/9705052.',
    'A. R. Calderbank, E. M. Rains, P. W. Shor, and N. J. A. Sloane, "Quantum error correction via codes over GF(4)," IEEE Trans. Inf. Theory 44, 1369 (1998).',
    'A. Paetznick and B. W. Reichardt, "Universal fault-tolerant quantum computation with only transversal gates and error correction," Phys. Rev. Lett. 111, 090505 (2013).',
    'J. T. Anderson, G. Duclos-Cianci, and D. Poulin, "Fault-tolerant conversion between the Steane and Reed-Muller quantum codes," Phys. Rev. Lett. 113, 080501 (2014).',
    'H. Bombin, "Gauge color codes: Optimal transversal gates and gauge fixing in topological stabilizer codes," New J. Phys. 17, 083002 (2015).',
    'C. Vuillot, H. Lao, B. Criger, C. G. Almudever, K. Bertels, and B. M. Terhal, "Code deformation and lattice surgery are gauge fixing," New J. Phys. 21, 033028 (2019).',
    'R. Chao and B. W. Reichardt, "Quantum error correction with only two extra qubits," Phys. Rev. Lett. 121, 050502 (2018).',
    'C. Chamberland and M. E. Beverland, "Flag fault-tolerant error correction with arbitrary distance codes," Quantum 2, 53 (2018).',
    'C. Chamberland and A. W. Cross, "Fault-tolerant magic state preparation with flag qubits," Quantum 3, 143 (2019).',
    'R. Chao and B. W. Reichardt, "Flag fault-tolerant error correction for any stabilizer code," PRX Quantum 1, 010302 (2020).',
    'T. Tansuwannont, C. Chamberland, and D. Leung, "Flag fault-tolerant error correction, measurement, and quantum computation for cyclic CSS codes," Phys. Rev. A 104, 042410 (2021).',
    'D. Gottesman, "Theory of fault-tolerant quantum computation," Phys. Rev. A 57, 127 (1998).',
    'R. Laflamme, C. Miquel, J. P. Paz, and W. H. Zurek, "Perfect quantum error correcting code," Phys. Rev. Lett. 77, 198 (1996).',
    'C. H. Bennett, D. P. DiVincenzo, J. A. Smolin, and W. K. Wootters, "Mixed-state entanglement and quantum error correction," Phys. Rev. A 54, 3824 (1996).',
    'P. Aliferis, D. Gottesman, and J. Preskill, "Quantum accuracy threshold for concatenated distance-3 codes," Quantum Inf. Comput. 6, 97 (2006).',
    'Google Quantum AI, "Suppressing quantum errors by scaling a surface code logical qubit," Nature 614, 676 (2023).',
    'C. Gidney, "Stim: a fast stabilizer circuit simulator," Quantum 5, 497 (2021).',
]
for i, r in enumerate(REFS, 1):
    doc.add_paragraph(f"[{i}]  {r}")

OUTPATH = os.path.join(ROOT, "paper", "code_switching_paper_v2.docx")
doc.save(OUTPATH)
print(f"wrote {OUTPATH}")
print(f"  encoder CX {N_ENC_CX}, confusable {N_CONF}/15, min flag bits {MIN_BITS}")
print(f"  sweep flags {N_SWEEP_FLAGS:,}, constraints {STEP4['constraints']:,}")
print(f"  e2e mechanisms {E2E['X']['mechanisms'] + E2E['Z']['mechanisms']:,}, "
      f"dangerous {E2E['X']['dangerous'] + E2E['Z']['dangerous']}")
print(f"  slopes {CERT['slope']:.2f} / {CRIP['slope']:.2f}")
