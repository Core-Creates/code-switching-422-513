# FINDINGS

Machine-checked record for the [[4,2,2]] to [[5,1,3]] code switch. Everything below is
computed by the scripts in this directory; no claim here was typed by hand.

## Contents

| part | what it covers |
|---|---|
| 1 | 16 numbered defects in the original manuscript, 5 of them fatal |
| 2 | the derived encoder and its two independent verifications |
| Lemma 1 | residual input errors are uncorrectable for every encoder |
| 3 | Step 2: flag placement search, and the encoder sweep over 24 cascades |
| 3b | the counting bound, and why every flag search was doomed |
| 4 | scaling of the fault enumeration to gates of any arity |
| 5 | recommended order of work (historical) |
| 6 | the teleportation switch and its joint-measurement certificate |
| 7 | the \|0>_L factory, and the corrected resource count |
| 8 | end-to-end certificate, and the three composition gaps it exposed |
| 9 | numerics: acceptance, logical error rate, and the measured exponent |
| 10 | adversarial validation, and the simplification it found |

Current headline numbers live in Part 10. Earlier parts record numbers as they stood when
written, and where a later part supersedes one it says so.

Reproduce with:


    python synthesize_encoder.py     # Step 0/1: conventions + encoder + 2 verifications
    python audit_paper_claims.py     # every load-bearing number in the manuscript
    python test_scaling.py           # fault-enumeration scaling tests
    python step2_flag_search.py      # Step 2: flag search + decoder synthesis
    python step2_encoder_sweep.py    # Step 2 outer loop: resynthesize and rerun
    python step4_two_flag_search.py  # counting bound and exact set cover
    python end_to_end.py             # the end-to-end certificate
    python validate_certificate.py   # attack the certificate
    python numerics.py               # Monte Carlo

---

## Part 1. Defects in the manuscript

Severity: **FATAL** breaks the protocol, **WRONG** is a false statement that must be
corrected, **EDITORIAL** is a presentation defect.

| # | Where | Finding | Severity |
|---|-------|---------|----------|
| 1 | Sec. 4.3 | "we measure the second logical operator Z2bar = ZIZI ... CNOT gates with q1 and q3 as controls". Sec. 3.1 defines `Z2bar = ZZII` and `Z1bar = ZIZI`. The Phase 2 circuit therefore measures `Z1bar`, destroying the logical qubit the protocol exists to preserve. Correct controls are q1 and q2. | FATAL |
| 2 | Sec. 3.3 | The gate list for `U` does not perform the code switch. Conjugating the six frame generators through it: `XXXXI -> -ZXXIY`, `ZZIII -> ZZIIZ`, `IIZZI -> IIZZZ`, `IIIIZ -> YIIXX`, `XXIII -> XXIIZ`, `ZIZII -> ZIZIZ`. Zero of six are correct, and the four stabilizer images are not even members of the [[5,1,3]] stabilizer group. | FATAL |
| 3 | Sec. 4.4, Sec. 5.4.1 | The flag gadget is broken under both readings. With `f` in \|0> as the target of CNOTs from q1, q2, q4, measuring `f` reveals `ZZIZI`, which is in neither stabilizer group and anticommutes with the output `Xbar = XXXXX` and with the input stabilizer `XXXX`: a destructive parity measurement, not a flag. With `f` in \|+> (F13's "H-CNOT-H sandwich"), `X\|+> = \|+>` makes the gadget exactly the identity: it flags nothing. | FATAL |
| 4 | Sec. 4.2 | The Phase 1 verification is a no-op. Ancilla `a3` in \|+> as the CNOT *target* is unaffected, so the measurement returns 0 regardless of `q5`. The claimed "yields 1 with probability 1/2" is wrong; the correct gadget prepares `a3` in \|0> and measures Z. | FATAL |
| 5 | Sec. 5.1 | "the re-encoding unitary is weight-preserving for weight-one errors by construction" is false, and no encoder can make it true. See Lemma 1. | FATAL |
| 6 | Sec. 5.4.1, 5.4.2 | All five hand-typed syndromes are wrong. `X5`: claimed (1,0,1,1), actual (0,0,1,1). `X1X5`: claimed (1,0,0,1), actual (0,0,1,0). `X2X5`: claimed (0,1,1,0), actual (1,0,1,1). `X3X5`: claimed (1,1,0,0), actual (1,1,1,1). `X4X5`: claimed (0,0,1,1), actual (0,1,0,1). | WRONG |
| 7 | Sec. 5.4.2 | "every flagged syndrome ... is distinct from the 15 weight-one syndromes" is impossible, not merely unproven. A perfect code has exactly 15 nonzero syndromes and exactly 15 weight-one errors, so every nonzero syndrome coincides with a weight-one syndrome. This follows from the perfectness the paper itself explains in Sec. 3.2. The flag bit is what disambiguates the decoder. | WRONG |
| 8 | Sec. 5.4.1 (F10) | "`Z_i Z_5` ... equivalent modulo stabilizers to a weight-1 error" is false for all three cases. `Z1Z5` decodes to a logical Y, `Z2Z5` and `Z3Z5` to a logical X. | WRONG |
| 9 | Abstract, Sec. 5, Sec. 8 | "any single physical fault produces at most a weight-one error on the output" contradicts Sec. 5.4.1, which produces weight-2 outputs at F2, F4, F5, F7, F8. The theorem should be flag-conditioned correctability (Chamberland-Beverland), not weight preservation. | WRONG |
| 10 | Sec. 5.4.1 (F5) | "f = 1 XOR 1 = 0 or f = 1 depending on exact topology. The flag-aware decoder handles all possibilities" is not an analysis; it is an admission that the circuit is undetermined. | WRONG |
| 11 | Abstract, Sec. 6.1, Sec. 8 | "approximately 15 CNOT gates" understates by roughly 5x. Exact two-qubit totals: Phase 0 = 8, Phase 1 = 1, Phase 2 = 2, Phase 3 = 17 (verified encoder, unoptimized) + 3 flag coupling, Phase 4 = 48 at r=3. Total 79. Phase 4 alone needs 48. | WRONG |
| 12 | Sec. 6.1, Sec. 4 | Qubit count inconsistent. Table 3 says 3 ancillas, but Sec. 4 names `a1..a4` and Sec. 4.5 measures four stabilizers "using one ancilla qubit" each. | WRONG |
| 13 | Sec. 3.3 | Two nearly identical paragraphs ("One can verify that the output states satisfy all four ... layered on top as shown in Figure 2") appear twice. | EDITORIAL |
| 14 | Table 1, Table 3 | Table 1 has four empty cells (Phase 1 Effect; Phase 3 X-type, Z-type, and Phase 4 Detection/Correction). Table 3 has an empty data-qubit row and an empty "Code distance improvement" value. | EDITORIAL |
| 15 | Byline, Algorithms 1 and 2 | Byline listed one author while Algorithm captions credited a second. RESOLVED: the authors are Corrina Alcoser, Keeban Villarreal and Michael Pendleton. Byline updated; the per-caption credits and the "4/20" working date removed as redundant. Confirm the affiliation line covers all three. | RESOLVED |
| 16 | Figures 1-4 | The four figures are static images that no longer agree with Sec. 3.3, Sec. 4.4, or Sec. 5.4. Figure 4 depicts a weight-3 error `X1X3X5` from a cascade whose gate list is defect 2. | EDITORIAL |

One hand-typed object in Sec. 3.3 is correct: the 16-term `|0bar>` expansion, which
evaluates to +1 on all four generators and on `Zbar`. It is the standard textbook
codeword.

---

## Part 2. Step 0 and Step 1 artifacts

`CONVENTIONS.md` is the single source of truth: qubit order, CNOT direction, the
`Z2bar = ZZII` rule with an explicit warning about defect 1, syndrome bit order, and
the input frame including its `(-1)^m` sign.

`synthesize_encoder.py` derives the encoder rather than guessing it. It completes each
frame to a symplectic basis by brute-force destabilizer search over all 4^5 Paulis,
builds both tableaux, composes `T_in^-1` with `T_out`, and lets Stim emit gates.

Verification 1 (tableau conjugation, signs included):

    U XXXXI U+ = +XZZXI      U XXIII U+ = +XXXXX
    U ZZIII U+ = +IXZZX      U ZIZII U+ = +ZZZZZ
    U IIZZI U+ = +XIXZZ
    U IIIIZ U+ = +ZXIXZ

Verification 2 (independent): the 32x32 unitary is rebuilt from `encoder.stim` in
float64 using our own gate matrices, sharing nothing with Stim's tableau algebra but
the circuit text. Leakage out of the [[5,1,3]] code space is 1.78e-15 and overlap with
the target codeword is 1.000000, for both logical states.

Resources, exact: **17 CX, 12 H, 15 S, 44 gate locations**, unoptimized. Optimization
is a separate later step with re-verification after every pass.

The `m=1` measurement branch is fixed by the input Pauli `IXIII`, which `U` maps to the
output Pauli `YIIYI`. Sec. 3.3 leaves this unspecified.

Note: Stim's `to_unitary_matrix` returns complex64. An early run showed 3.4e-8 leakage
purely from float32 rounding. This is worth stating because it is exactly the kind of
number that gets copied into a paper as a physical result.

---

## Lemma 1 (residual input errors are uncorrectable, for every encoder)

Let the input be the post-Phase-2 frame `<XXXXI, ZZIII, IIZZI, IIIIZ>` with logicals
`Xbar = XXIII`, `Zbar = ZIZII`. Partition the 15 weight-one Paulis by input syndrome:

| syndrome | errors | status |
|---|---|---|
| (0,0,0,0) | `IIIIZ` | correctable |
| (0,0,0,1) | `IIIIX`, `IIIIY` | correctable |
| (0,0,1,0) | `IIXII`, `IIIXI` | confusable |
| (0,1,0,0) | `XIIII`, `IXIII` | confusable |
| (1,0,0,0) | `ZIIII`, `IZIII`, `IIZII`, `IIIZI` | confusable |
| (1,0,1,0) | `IIYII`, `IIIYI` | confusable |
| (1,1,0,0) | `YIIII`, `IYIII` | confusable |

**12 of the 15 lie in a confusable pair**: same syndrome, product not a stabilizer.
`X1` and `X2` share syndrome (0,1,0,0) and differ by `XXIII = X1bar`, which is just
what distance 2 means. A Clifford is an isomorphism of the Pauli algebra, so the images
are syndrome-identical and differ by the output logical under *every* valid `U`. No
downstream decoder can separate them.

**At most 3 of the 15 are correctable by any encoder and any decoder**, and 3 is
achieved: under our `U`, `Z5 -> ZXIXZ = g4` (a stabilizer, harmless) and
`X5 -> ZXYZZ`, `Y5 -> IIYYI` share syndrome (0,0,0,1) and differ by a stabilizer, so a
*synthesized* decoder mapping (0,0,0,1) to `ZXYZZ` corrects all three. The standard
weight-one [[5,1,3]] table does not, which is why applying it makes 14 of 15 fail.

Consequences the manuscript must absorb:

1. Sec. 5.1's argument is void. Phase 0's post-selection is load-bearing, so its fault
   tolerance belongs inside the theorem, not in a remark.
2. Scope is a state-preparation factory unless discard-and-restart is replaced by frame
   updates. Say which, in the abstract.
3. Sec. 5.2 inverts: errors on `q5` are the correctable ones, so Phase 1's verification
   is a rate optimization, not a fault-tolerance requirement.

---

## Part 3. Step 2, flag placement and decoder synthesis

Method: for each candidate flag design, (1) check it is a valid flag at all, (2) run the
complete single-fault enumeration, (3) bucket by (syndrome, flag) and try to synthesize
one correction per bucket that works for every fault in it, up to stabilizers. A design
whose buckets mix logically inequivalent residuals is rejected.

**Fault model.** Every gate of arity `k` contributes all `4^k - 1` non-identity Paulis
on its support, applied immediately after the gate. Preparation faults on the fresh
`q5` and on each flag ancilla. A classical flip of each flag readout. Optionally, idle
faults: X, Y, Z on every qubit at every circuit slot. Faults acting trivially on a fresh
ancilla (Z on \|0>, X on \|+>) are excluded as unphysical. Out of scope by Lemma 1:
errors already present on the data block when Phase 3 begins. Phase 4 is assumed ideal;
it is Chao-Reichardt's gadget and carries its own certificate.

**Flag design space.** A flag is a bracketing CNOT pair on one data qubit: kind `X`
uses `f` in \|0> with `CX(d->f)` at two slots and Z-basis readout; kind `Z` uses `f` in
\|+> with `CX(f->d)` and X-basis readout. A candidate is only a flag if, in the
fault-free run, the readout is deterministic *and* the encoder's frame map is unchanged.
Of 9900 single-flag candidates, **3474 are valid**; the other 6426 either fire without a
fault or corrupt the code switch.

### Results

| design space | fault locations | undecodable buckets |
|---|---|---|
| no flag, gate-only | 337 | 16 of 16 |
| no flag, gate + idle | 1010 | 16 of 16 |
| best single flag, strict (flagged faults corrected) | 369 | 16 |
| best single flag, post-selected (flagged faults discarded) | 369 | 15 |
| best two-flag pair from the 30 best singles | 401 | 16 |

**No design in the searched space certifies Phase 3.** Not one of the 3474 valid single
flags, and not one of the 435 searched pairs, yields a decodable bucket set under either
criterion. The bare cascade fails all 16 buckets, and the best flag removes at most one.

Representative collisions in the unflagged baseline, all at syndrome-identical
locations differing by a logical operator:

    syndrome (1,0,0,0): g0:H(0) X   vs  g4:CX(0,1) YZ [differs by logical X]  vs  g7:H(2) X [logical Z]
    syndrome (1,1,0,0): g0:H(0) Y   vs  g2:S(1) X [logical X]                 vs  g14:CX(4,2) YI [logical Y]
    syndrome (0,1,0,0): g0:H(0) Z   vs  g2:S(1) Y [logical X]                 vs  g12:CX(1,2) ZX [logical Z]

The pattern is that faults in the first few gates spread to weight 5 and 6 by the end of
a 44-location serial cascade, and land on top of each other modulo logicals. This is a
property of the cascade, not of the flag: a bracketing pair can only separate faults it
brackets, and no single interval brackets enough of them.

### Step 2 outer loop: resynthesize the cascade and rerun

The frame map has freedom, since which input stabilizer is sent to which [[5,1,3]]
generator is a choice (4! = 24 bijections), and each yields a different cascade with
different error-spreading structure. `step2_encoder_sweep.py` resynthesizes the encoder
for all 24 and reruns the entire flag search on each. Per-cascade results are in
`sweep_rows.jsonl`.

| quantity | result over all 24 cascades |
|---|---|
| two-qubit gate count | 15 to 25 (our default bijection gives 17) |
| unflagged baseline undecodable buckets | 15 or 16, always |
| valid single-flag designs searched | **97,466** |
| designs that certify Phase 3 | **0** |
| best undecodable-bucket count achieved | 14 of 16 |
| best cascade | bijection (3,2,0,1), 16 CX, flag `('X', d=3, slots 11 and 25)`, 14 bad |

So the negative result is not an artifact of one arbitrary encoder. Across every
stabilizer bijection, and across 97,466 valid bracketing-pair flags, the best design
still leaves 14 of 16 buckets mixing logically inequivalent residuals. A single
bracketing-pair flag is structurally too weak for this cascade: it separates only the
faults it brackets, and the collisions are spread across the whole circuit.

The smallest cascade found is 15 CX, which is the number to quote if a resource
comparison is needed. It is still not 6, and the paper's "approximately 15 CNOT gates"
for the *entire five-phase protocol* remains wrong by roughly 5x.

---

## Part 3b. Why every flag search failed: a counting bound

The searches above were exploring a family that is provably too small, and one cheap
computation shows it.

Partition the Phase 3 single-fault locations by their [[5,1,3]] syndrome. There are 16
classes. Count the logically inequivalent residuals in each:

    distinct residual classes per syndrome: [4,4,4,4,4,4,4,4,4,4,3,3,3,3,3,3]
    worst class, syndrome (1,0,0,0): 4 inequivalent residuals

A decoder keyed on (syndrome, flag) can only split each syndrome class into `2^b` groups,
where `b` is the number of flag bits. Separating 4 inequivalent residuals therefore needs

    b >= ceil(log2 4) = 2 flag bits

**No single flag can ever certify this cascade, wherever its couplings are placed.** That
is placement-independent, it holds for the gate-only and gate+idle fault models alike,
and it explains all 97,466 failures in Part 3 at a stroke. The manuscript's single flag
qubit is not merely badly placed; it carries one bit where two are needed.

### Step 3: the widened flag family

Flags with three and four couplings, and couplings touching different data qubits, which
the bracketing-pair family cannot express. Tractability comes from an algebraic
prefilter: the data part of the measured flag operator's image is the XOR of per-coupling
keys, so a necessary condition for a deterministic readout is that those keys cancel. Two
integer XORs per coupling, no tableau. It cuts the size-3 space from 1,873,200 candidates
to 6,133, and 97 percent of survivors turn out to be genuinely valid.

Sizes 2 and 3 exhaustive: **17,287 valid flags, 0 certifying**, best still 16 of 16 bad
buckets. Exactly as the bound predicts.

### Step 4: two flag bits, and how many would actually be needed

With the bound saying 2 bits is the minimum, the question is whether some pair works. We
recast it as exact set cover. Each constraint is a pair of faults in the same syndrome
class with inequivalent residuals that must receive different labels; each flag covers
the constraints where its bit differs; a certifying pair is two flags whose coverage
unions to everything. Branching on the rarest constraint makes the pair search exact
rather than quadratic.

| quantity | result |
|---|---|
| separation constraints | 2,405 |
| candidate flags (sizes 2, 3 and 4, all exhaustive) | 867,694 |
| distinct coverage patterns | 5,384 |
| single flags covering everything | 0 |
| **pairs covering everything** | **0** |
| constraints coverable by no flag at all | 0 |
| greedy cover size | **9 flag bits** |

Every constraint is separable by some flag, so there is no absolute obstruction. The
obstruction is combinatorial: coverage is spread so thinly that two bits cannot reach it,
and a greedy cover needs nine. Nine is an upper bound from a heuristic, not the true
minimum, and the particular nine-flag combination greedy selected is not even jointly
valid. But the gap between the lower bound of 2 and a greedy cover of 9 is decisive at
the engineering level: flag-protected re-encoding of this cascade would need roughly an
order of magnitude more ancillas than the manuscript claims, which puts it well past the
cost of the teleportation-based switch that Section 6.2 dismisses.

**Recommendation.** Phase 3 should not be flag-protected. Redo the Section 6.2 comparison
against the corrected counts and adopt either teleportation or a measurement-based switch
via gauge fixing. The counting bound and the empty pair search are themselves a result
worth stating: they explain why the obvious construction cannot work, which is more
useful to a reader than another circuit that happens to fail.

### What this does NOT establish

Stated explicitly so it cannot be over-read:

- Not "flag-based code switching is impossible". The search covers bracketing-CNOT-pair
  flags, one and two of them, over the cascades produced by Stim's `elimination`
  synthesis from the 24 stabilizer bijections. Stim's `graph_state` synthesis method
  was excluded because it emits reset operations and so is not a unitary re-encoder.
- The two-flag stage was run only on the default bijection, not on all 24 cascades.
- The single-flag family is now EXHAUSTIVE at 2, 3 and 4 couplings: the full primitive
  size-4 space is 849,381 subsets and all of it was searched, so
  the negative result is not an artifact of sampling. The greedy cover size of 9 remains
  a heuristic upper bound, not the true minimum, and no lower bound above 2 is proved.
- The two-flag stage searches only pairs drawn from the 30 best singles, not all
  ~6 million valid pairs. This is a bounded search, and the bound is logged.
- Flags with more than two CNOTs, flags coupling to more than one data qubit, and
  measurement-based or teleportation-based Phase 3 designs are unsearched. Sec. 6.2
  dismisses teleportation on a resource argument that defect 11 shows was computed
  against a 5x-understated baseline; that comparison should be redone.

### Two superseded runs, recorded so the numbers are traceable

1. A first search over 2760 candidates reported "0 survive" without a validity filter,
   so most candidates were not flags at all. Superseded.
2. That same run treated Stim's batched targets as single gates, so `H 1 2` became a
   two-qubit location and `CX 0 1 0 4` became one gate. The fault model was wrong in
   both directions and the two-qubit gate count read 7 instead of 17. Fixed by
   `flagsearch.split_ops`, which splits one Op per gate using gate arity.

---

## Part 4. Scaling of the fault enumeration

The enumeration is arity-generic: a fault location is a gate of any arity `k`, and it
contributes all `4^k - 1` non-identity Paulis on its support, so correlated multi-qubit
faults are covered by construction (k=1: 3, k=2: 15, k=3: 63, k=4: 255, k=5: 1023).
Arity comes from Stim's gate metadata with an override hook for gates Stim does not
model natively (CCZ, CCX, Molmer-Sorensen). Multi-qubit parity measurements (`MPP`)
become one location whose support is the whole Pauli product. Consecutive gates can be
fused into an atomic macro location for hardware whose native multi-qubit gate fails as
a unit. Any weight restriction is reported by `fault_model_summary`, never silent.

Propagation stays O(k) per fault regardless of circuit length: per slot we precompute
the image of each single-qubit generator under the suffix circuit, so a fault Pauli's
image is an XOR of those.

`test_scaling.py` checks all of this, including a regression that the arity-generic path
reproduces the arity-1/2 numbers exactly (44 gate locations, 17 CX, 337 fault locations,
16 undecodable buckets).

---

## Part 5. Recommended order of work

1. Fix `CONVENTIONS.md` into the manuscript and regenerate Sec. 3 from it.
2. Replace Sec. 3.3's gate list with `encoder.stim` and its two verifications.
3. State Lemma 1 and re-scope the abstract to a state-preparation factory.
4. Phase 3 needs a different structure. The sweep closes the "one or two bracketing-pair
   flags over a resynthesized cascade" family: 97,466 designs, none certifies. The next
   moves, in increasing order of departure from the current draft, are (a) richer flag
   families (more than two couplings per flag, three or more flags, flags on several
   data qubits), (b) a measurement-based Phase 3 via gauge fixing, (c) the
   teleportation-based switch the paper dismisses in Sec. 6.2 on a resource comparison
   that defect 11 invalidates. Redo that comparison against the exact counts before
   choosing.
5. Replace Phase 4 with Chao-Reichardt's [[5,1,3]] flag gadget, already cited as [9].
6. Restate the theorem as flag-conditioned correctability (Chamberland-Beverland, [10]).
7. Numerics: Stim Monte Carlo vs unflagged and teleportation baselines, plus acceptance
   rate vs p, since Phase 0 post-selection is now provably load-bearing.
8. Generate Figures 1-4 from the same `.stim` file the simulator runs, and script-generate
   every table.
9. Write in order: theorem, Sec. 3-5, numerics, related work, introduction, abstract last.

---

## Part 6. The teleportation switch (Step 5)

With the flag-protected re-encoding route closed, this is the alternative Section 6.2
dismissed. It verifies, and its critical gadget certifies.

### The protocol

One-bit teleportation by joint logical measurement, so no cross-code CNOT is needed:

1. verify block A, the [[4,2,2]] block, by measuring XXXX and ZZZZ, post-select
2. prepare block B, a fresh [[5,1,3]] block, in `|0>_L` and verify it
3. measure `M1 = X1bar_A (x) Xbar_B = XXII (x) XXXXX`, weight 7
4. read A out destructively in the Z basis, giving `M2 = Z1bar` and a free ZZZZ check
5. Pauli frame update on B: `Xbar^(m2 + b5) Zbar^(m1)`

`teleport_switch.py` verifies the ideal identity by sampling: the parities
`out + a_log + m1` (X basis) and `out + a_log + m2 + b_zbar` (Z basis) are deterministic
over 4096 shots while every individual outcome is random. Both logical operators
teleport.

Three structural advantages, and the third is the one that matters:

- **Phase 2 disappears.** The second logical qubit is discarded with the block, so there
  is no `Z2bar` measurement and defect 1 has nothing to attach to.
- **A is destroyed.** Its destructive Z readout costs no two-qubit gates and hands back
  the ZZZZ stabilizer as a free check, so any odd-weight X-type error on A is detected.
- **The protected object is a Pauli measurement, not an encoder.** Every gate in the
  cascade is `CX(m -> data)` with the same control, and a flag gadget is `CX(m -> f)`.
  Gates sharing a control commute, so the flag pair cancels exactly for ANY bracketing.
  In the re-encoding cascade the intervening gates did not commute with the flag pair,
  which is why only 3474 of 9900 bracketings were valid flags there. **That is the real
  reason flags are standard for syndrome extraction and failed for re-encoding.**

### Certificate for the joint measurement

Fault model as elsewhere, plus two corrections that had to be made to make the count
physical rather than formal: an error lying in the stabilizer group of the state at that
point is not a fault (X on the ancilla just after the H, where it is in `|+>`), and two
errors differing by an ancilla-local stabilizer are the same fault (Y there is just Z).
Reduction is restricted to ancilla-local elements, since a stabilizer touching the data
blocks, `Zbar_B` for one, would silently relabel the logical class.

| design | fault locations | discarded | surviving | undecodable buckets |
|---|---|---|---|---|
| no flag | 113 | 16 | 97 | 9 of 16 |
| one flag bracketing the cascade | 142 | 83 | 59 | **0 of 16** |

The synthesized decoder is exactly the standard weight-one [[5,1,3]] lookup: each of the
15 nonzero syndromes maps to the corresponding single-qubit Pauli and the trivial
syndrome to the identity. That is the signature of a gadget behaving, since it says the
surviving errors on B really are weight one. A sample of 138 of the 5040 coupling orders
against all 28 valid brackets yields 407 certifying designs, so the result is not
delicate.

### Resources

| route | two-qubit gates |
|---|---|
| teleportation switch | 59 |
| flag re-encoding switch | 79 |

The `|0>_L` preparation for B is 26 CX, synthesized from the frame and verified the same
way the re-encoder was. Section 6.2's claim that teleportation costs more was made
against a baseline understated fivefold; on the corrected numbers it is cheaper, and it
is the route that certifies.

### Not yet established

- Fault tolerance of the `|0>_L` preparation for B, which is assumed ideal here. It needs
  its own verified circuit and certificate.
- The end-to-end enumeration across all five steps, rather than the joint measurement
  alone.
- Reliability of the M1 outcome is handled by repetition; the single-round analysis
  treats a bare outcome flip with no data error as benign, which is what `r >= 3` and
  majority vote buy. A separate argument is still owed for the correlated case.
- The coupling-order search sampled 138 of 5040 orders. Brackets are exhaustive.

---

## Part 7. The |0>_L factory (Step 6), and the corrected resource count

The last unproven piece of the teleportation switch. It certifies, and for a reason that
is worth stating in the paper because it is not obvious.

### B does not need to be in |0>_L

The teleportation identity carries the frame Pauli `Xbar^(m2 + b5) Zbar^(m1)`, where `b5`
is the recorded outcome of the `Zbar` measurement on B. So B need only be IN THE CODE
SPACE. Which of the two logical states it holds is recorded, not required. Every single
fault in preparation therefore falls into one of three cases and there is no fourth:

| outcome of a single prep fault | count |
|---|---|
| detected by the g1..g4 syndrome, shot discarded | 124 |
| a stabilizer, so not an error at all | 3 |
| a logical operator, absorbed by the frame bit b5 | 3 |
| **uncorrectable** | **0** |

The preparation circuit itself is **6 two-qubit gates**, from graph-state synthesis
rather than full-Clifford elimination: only the Z-images are constrained for a state, and
exploiting that takes it from 26 CX to 6.

Verification cascades were checked the same way. With or without flags, no fault leaves
the block outside the code space: 288 of 384 discarded with a flag per generator, 96
surviving, 0 escaping.

**Ordering requirement.** The absorption argument is not a free lunch. The `Zbar` frame
measurement must be performed AFTER the g1..g4 verification. A logical fault arriving
after `b5` is recorded leaves the frame bit stale, and a stale frame bit is a logical
error on the output rather than an absorbed one. This is a real constraint on the
protocol and it must appear in the theorem, not in a remark.

### Corrected resource count

The figure of 59 quoted in Part 6 did not cost B's verification. Honestly:

| step | two-qubit gates |
|---|---|
| verify A: measure XXXX and ZZZZ | 8 |
| prepare B in |0>_L | 6 |
| verify B: g1..g4 cascades | 16 |
| verify B: one flag per generator | 8 |
| verify B: Zbar frame measurement | 5 |
| joint M1, weight 7, r = 3 | 21 |
| M1 flag, r = 3 | 6 |
| read A out destructively in Z | 0 |
| **total** | **70** |

Against 79 for the flag re-encoding route. So the two are comparable on gate count, and
the resource argument is NOT the reason to prefer teleportation. The reason is that this
one has a certificate and the other cannot have one at any price: the counting bound
forces at least 2 flag bits, no pair of flags covers the constraints, and greedy needs 9.

That is the honest framing for Section 6.2, and it is the opposite of the draft's claim
in both directions: teleportation is not more expensive, and it is not merely an
alternative, it is the only one of the two that works.

### Still open

- End-to-end enumeration across all steps at once, rather than per gadget. Each gadget
  now has a certificate; composing them is a separate obligation.
- The correlated case in which one fault both flips an M1 outcome and leaves a data
  error. Repetition handles the outcome, but the argument is still owed.
- Numerics: logical error rate and acceptance rate versus p. Acceptance is now the
  interesting one, since 83 of 142 M1 fault locations and 288 of 384 verification fault
  locations lead to a discard.

---

## Part 8. End-to-end enumeration (Step 7): the protocol is fault tolerant

Per-gadget certificates do not compose, and this run proves it: the whole protocol is
built as one stim circuit with a DETECTOR for every post-selection check and an
OBSERVABLE_INCLUDE for the teleported logical, and a single fault is dangerous exactly
when it flips the observable while firing no detector. Stim's detector error model
enumerates every fault mechanism, so the check is a scan of that model rather than an
argument.

| logical basis | single-fault mechanisms | undetectable logical errors |
|---|---|---|
| Xbar | 609 | **0** |
| Zbar | 667 | **0** |

**Positive control.** Removing the M1 flag reintroduces a dangerous mechanism, so the
scan can fail and a clean result carries information. An earlier control that merely
blinded one arbitrary flag detector returned 0, which proved nothing; it was replaced.

### Three composition gaps the per-gadget certificates could not see

Each of these passed inside its own gadget and failed in context. They are the substance
of this step.

1. **The `Zbar` frame measurement was unprotected.** It sits between two certified
   gadgets. Its weight-5 cascade had no flag and no repetition, so one fault could flip
   `b5`, and a stale frame bit is a logical error. Fixed by flagging it, repeating it,
   and adding a second B verification round after it, since errors it injects into B
   would otherwise face no further check before M1 couples to the block.
2. **No hand-off EC round on B.** Errors injected into B by the M1 cascades were never
   checked. Fixed with a final verification round, taken noiseless by convention: it
   stands for the receiving computation's own first error-correction cycle, which is
   where a real switch hands the block over.
3. **A's verification was not interleaved with M1.** A Z error landing on A during an M1
   cascade flips the M1 outcome in every later round identically, so the round-to-round
   detectors cannot see it. It anticommutes with XXXX, so an interleaved XXXX check
   between M1 rounds catches it. This is the correlated case that was previously owed as
   a separate argument; it is now just another fault location.

### Honest resource count

Counted from the circuit: **162 two-qubit gates**, including the noiseless hand-off round.
This is the real number for a fully certified protocol, against the 70 quoted in Part 7
for the gadget-level assembly and the 79 for a flag re-encoding route that has no
certificate at any price. Protection is most of the cost, which is the expected result and
should be stated plainly rather than buried.

### Remaining

Numerics: logical error rate and acceptance rate versus p. Acceptance is now the number
that decides practicality, and it is not small: post-selection is load-bearing at every
stage.

---

## Part 9. Numerics (Step 8)

Circuit-level depolarizing noise, 4,000,000 shots per point, taken from the same
end-to-end circuit that carries the certificate. Acceptance is the fraction of shots in
which no detector fires; the logical error rate is measured among accepted shots only.

### Certified protocol

| p | acceptance | accepted shots | logical errors | p_L |
|---|---|---|---|---|
| 0.001 | 0.799 | 3,195,400 | 19 | 5.9e-06 |
| 0.002 | 0.639 | 2,554,955 | 75 | 2.9e-05 |
| 0.003 | 0.511 | 2,042,655 | 128 | 6.3e-05 |
| 0.005 | 0.326 | 1,304,088 | 250 | 1.9e-04 |
| 0.007 | 0.209 | 834,562 | 292 | 3.5e-04 |
| 0.010 | 0.107 | 426,841 | 355 | 8.3e-04 |

**Fitted slope of log p_L against log p: 2.11.** With the M1 flag removed: **1.15**.

That agreement is the point. The end-to-end enumeration is combinatorial and says no
single fault produces an undetectable logical error, which forces the leading term to be
quadratic. The Monte Carlo is statistical and independently measures an exponent of 2.11.
The crippled variant, which has exactly one single-fault mechanism, measures 1.15. A
proof and a measured exponent agreeing is worth more than either alone, and a slope near
1 for the certified protocol would have meant the enumeration missed something.

`p_L` stays below `p` across the whole sampled range, so the pseudothreshold lies above
1e-2 and outside the window sampled here.

### Acceptance is the practical constraint

Post-selection is load-bearing at four separate stages: A's input verification, B's
preparation verification, every flag, and the ZZZZ parity of A's destructive readout.
The cost shows up here and nowhere else:

- at p = 1e-3, roughly 80 percent of shots are accepted, which is workable
- at p = 1e-2, roughly 11 percent are accepted, so the factory yields about one block in
  nine

This is the number the draft never had, and it is the one that decides whether the
protocol is practical. It also confirms the scope forced by Lemma 1: this is a
state-preparation factory, and its yield is a first-class figure of merit rather than a
remark. Anyone quoting the gate count without the acceptance rate is quoting half the
cost.

---

## Part 10. Adversarial validation, and a simplification it found

`validate_certificate.py` attacks the end-to-end certificate from the directions where it
could be vacuous rather than true. A clean fault scan means nothing if the scan could not
have come out dirty.

| check | result |
|---|---|
| no gauge detectors (model rebuilt with tolerance off) | clean in both bases |
| no dead detectors | 0 of 28 never fire |
| observable is live | flips in 1,489 and 3,303 of 20,000 shots |
| distance is exactly two | a two-fault logical failure exists in both bases |
| every protection load-bearing | see below |

The last check is the one that paid. Removing each protection in turn and requiring the
scan to fail found that **three of the eight protections were not load-bearing at all**:
the second round of A verification, the flag on the Zbar frame measurement, and the second
B verification round after Zbar. Removing all three jointly still certifies.

Numerics then settled whether they helped at second order, where the single-fault scan is
blind. They do not:

| p | variant | two-qubit gates | acceptance | p_L |
|---|---|---|---|---|
| 0.005 | full | 162 | 0.327 | 2.12e-04 |
| 0.005 | simplified | 120 | **0.459** | 2.00e-04 |
| 0.010 | full | 162 | 0.107 | 7.80e-04 |
| 0.010 | simplified | 120 | **0.212** | 7.31e-04 |

Same logical error rate within statistics, nearly double the yield, 42 fewer two-qubit
gates. Those three protections were pure cost. **The simplified protocol is now the
protocol**, and re-validation confirms all five surviving protections are load-bearing.

This is worth recording as a methodological point, not just a result. The three were added
during end-to-end debugging in a single batch, when the scan went from failing to passing.
Adding protections until a check passes is how gadgets become over-engineered: nothing in
that process tells you which addition did the work. Ablation does, and it should be a
standard step rather than an afterthought.

### Updated headline numbers

- two-qubit gates: **120**, down from 162
- detectors: 28, down from 43
- single-fault mechanisms: 824, zero dangerous
- acceptance: **86%** at p = 1e-3 and **21%** at p = 1e-2, up from 80% and 11%
- fitted exponent: **2.17**, against 1.13 for the crippled control

---

## Part 11. Tuning, and a recommendation I had to withdraw

Two questions the certificate cannot answer, in `tune_protocol.py`.

### Repetition counts

`r = 3` for the M1 and Zbar measurements was chosen by convention. Ablating it:

| M1 rounds | Zbar rounds | 2q gates | certificate | acceptance | p_L (p = 5e-3) |
|---|---|---|---|---|---|
| 1 | 1 | 80 | fails |  |  |
| 1 | 2 | 85 | fails |  |  |
| 1 | 3 | 90 | fails |  |  |
| 2 | 1 | 95 | fails |  |  |
| 2 | 2 | 100 | certifies | 0.5317 | 3.699e-04 |
| 2 | 3 | 105 | certifies | 0.5131 | 2.436e-04 |
| 3 | 1 | 110 | fails |  |  |
| 3 | 2 | 115 | certifies | 0.4753 | 2.244e-04 |
| 3 | 3 | 120 | certifies | 0.4598 | 2.139e-04 |

`r = 1` fails outright: with one round there is no round-to-round detector to catch a
measurement flip. `r = 2` certifies, uses 20 fewer gates and yields 7 points more.

**I initially recommended r = 2 on that basis, and it was wrong.** The tuning script
measured acceptance and gate count but not logical error rate, and r = 2 pays for its
savings with a factor of about 1.7 in p_L. For a factory whose product is a low-error
encoded state, p_L is the objective and yield is the budget. The protocol keeps r = 3, and
the script now measures the objective it is optimising.

Zbar at r = 2 against r = 3 is within Poisson noise on these counts, so the extra round is
neither justified nor ruled out by this data. It stays at 3 rather than churn on a null
result.

The lesson generalises past this protocol: an ablation is only as good as the metric it
scores. Removing three protections earlier was right because p_L was unchanged and yield
doubled. Removing a repetition round looked identical on the metrics I was watching and
was not.

### Where the yield goes, at p = 5e-3

| stage | detectors | fire rate |
|---|---|---|
| B verify | 12 | 0.3336 |
| A verify | 4 | 0.0868 |
| A interleave | 4 | 0.1152 |
| M1 flag | 3 | 0.0962 |
| Zbar repeat | 2 | 0.0731 |
| M1 repeat | 2 | 0.1129 |
| A readout | 1 | 0.0737 |

B's verification discards most, by a wide margin: it alone would cap acceptance at
0.6664. That is where yield work would pay, and it is the
first thing to look at if this protocol is ever run at scale.

### Uncertainty on the measured exponent

The exponent is now quoted with a bootstrap over the per-point error counts:
**2.01 +/- 0.08** for the certified protocol against
**1.11 +/- 0.01** for the crippled control, separating the two
regimes by 11
standard deviations. A slope quoted without an uncertainty is not a claim a referee can
check.
