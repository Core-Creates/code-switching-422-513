# code-switching-422-513

Verified artifacts for fault-tolerant code switching from the [[4,2,2]] error-detecting
code to the [[5,1,3]] perfect code.

The manuscript is generated from this repository, not the other way round. Every circuit,
every syndrome, every gate count and every table entry is produced by a script and pinned
by a test. Nothing is typed by hand into the paper.

## What this establishes

**Lemma 1.** Of the fifteen weight-one errors present on the data block when re-encoding
begins, twelve lie in a confusable pair and are correctable by no encoder and no decoder.
Only the three on the fresh ancilla are correctable. The initial post-selection is
therefore load-bearing, and the protocol is a state-preparation factory rather than an
in-line switch.

**Flag-protected re-encoding cannot be certified, at any flag budget.** Partitioning the
single-fault locations by syndrome leaves three or four logically inequivalent residuals in
every one of the sixteen classes, so at least two flag bits are necessary regardless of
placement. Search confirms the bound is not loose: 97,466 valid single-flag designs across
all twenty-four stabilizer bijections certify nothing, and an exact set-cover analysis of
two-bit designs over 2,405 separation constraints and 5,384 distinct coverage patterns
finds no covering pair. A greedy cover needs nine bits.

**A teleportation-based switch does certify.** End-to-end single-fault enumeration over 824
mechanisms finds no undetectable logical error in either logical basis, corroborated by a
measured error-rate exponent of 2.17 against 1.13 for a deliberately crippled control. It
uses 120 two-qubit gates, and post-selection accepts 86 percent of shots at p = 1e-3 and 21
percent at p = 1e-2.

The structural reason the second works where the first cannot: in a measurement cascade
every gate shares the ancilla as control, so a flag pair commutes with the cascade and
cancels for any bracketing. In an encoding cascade it does not. **Protect measurements, not
encoders.**

## Layout

| path | what it is |
|---|---|
| `CONVENTIONS.md` | single source of truth: qubit order, gate direction, logical operators, syndrome bit order, frame bookkeeping |
| `FINDINGS.md` | the full record: manuscript audit, both no-go results, every certificate, and the limits of each |
| `frames.py` | the stabilizer frames and the symplectic completion used to build tableaux |
| `flagsearch.py` | arity-generic fault enumeration, flag validation, decoder synthesis |
| **Step 1** | |
| `synthesize_encoder.py` | derives the re-encoding Clifford and verifies it two independent ways |
| `encoder.stim` | the derived encoder, 17 CX / 12 H / 15 S, unoptimized |
| `audit_paper_claims.py` | checks every load-bearing number in the original draft |
| **Steps 2 to 4, the no-go** | |
| `step2_flag_search.py` | exhaustive flag placement search over one cascade |
| `step2_encoder_sweep.py` | resynthesize the cascade and rerun, all 24 bijections (resumable) |
| `step3_wide_flag_search.py` | the widened flag family: three and four couplings, across data qubits |
| `step4_two_flag_search.py` | two-bit designs as exact set cover, plus the counting bound |
| **Steps 5 to 8, the protocol** | |
| `teleport_switch.py` | the teleportation identity, verified by sampling |
| `teleport_fault_analysis.py` | certificate for the joint logical measurement |
| `prep_factory.py` | certificate for the \|0>_L factory for block B |
| `end_to_end.py` | the whole protocol as one circuit, with the end-to-end certificate |
| `validate_certificate.py` | adversarial validation: is the certificate vacuous or true? |
| `numerics.py` | Monte Carlo: acceptance and logical error rate against p |
| `qiskit_export.py` | translation to Qiskit and cross-check on Aer |
| **Output** | |
| `paper/generate_manuscript.py` | generates the manuscript from the artifacts |
| `paper/make_figures.py` | generates both figures from the circuits and results |
| `results/` | every result file the manuscript reads |
| `paper_edits/` | the scripted tracked-change audit of the original draft |
| `tests/` | pytest suite pinning all of the above |

## Quick start

    pip install -r requirements.txt
    pytest                  # fast suite, seconds
    pytest -m slow          # adds the exhaustive searches, minutes

In pipeline order:

    python synthesize_encoder.py      # Step 1: rebuild and re-verify encoder.stim
    python audit_paper_claims.py      # the original draft's numbers, checked
    python step2_flag_search.py       # flag search over the default cascade
    python step2_encoder_sweep.py     # sweep all 24 cascades
    python step4_two_flag_search.py   # counting bound and exact set cover
    python teleport_switch.py         # the teleportation identity
    python teleport_fault_analysis.py # certificate for the joint measurement
    python prep_factory.py            # certificate for the |0>_L factory
    python end_to_end.py              # the end-to-end certificate
    python validate_certificate.py    # attack the certificate
    python numerics.py                # Monte Carlo
    python qiskit_export.py           # Qiskit translation and Aer cross-check
    python paper/make_figures.py && python paper/generate_manuscript.py

## Fault model

Stated once, here and in `end_to_end.py`, and never restated informally.

Every gate of arity `k` contributes all `4^k - 1` non-identity Paulis on its support, so
correlated multi-qubit faults are covered for any `k`. Preparation faults act on every
fresh ancilla; measurement faults flip every classical outcome. An error lying in the
stabilizer group of the state at that point is not a fault, and two errors differing by an
ancilla-local stabilizer are the same fault. Without those two reductions the count is
formal rather than physical.

Arity comes from Stim's gate metadata, with an override hook for gates Stim does not model
natively (CCZ, CCX, Molmer-Sorensen). `MPP` parity measurements become one location
spanning the whole Pauli product, and consecutive gates can be fused into an atomic macro
location for hardware whose native multi-qubit gate fails as a unit. Any weight restriction
is reported by `fault_model_summary`, never applied silently.

Errors already present on block A when the protocol begins are out of scope by Lemma 1:
they are the post-selection's problem, not the protocol's.

## Running it on Qiskit

    python qiskit_export.py

The circuit is translated from the certified stim circuit rather than reimplemented, so
there is no second copy to keep correct. Two properties make the port straightforward:

- **No feed-forward.** The Pauli frame update is classical bookkeeping on the final
  readout, not a conditional gate, so the exported circuit is static. A test asserts no
  conditional operation appears. This matters where dynamic circuits are slow or
  restricted.
- **Detectors become bit parities.** Qiskit has no detector concept, so each becomes an
  index set over the shot bitstring; a shot is accepted when all parities are zero.

Noise is translated instruction by instruction with stim's exact probabilities, so the Aer
comparison tests the translation and not two simulators' noise conventions. The noiseless
protocol is deterministic in Aer in both bases, all per-detector firing rates agree within
shot noise, and acceptance agrees at 0.7 sigma at 120,000 shots.

**Hardware caveat.** The certificate covers this circuit. Transpiling onto a restricted
coupling map inserts SWAPs, three CX gates apiece that the fault enumeration never saw, so
a transpiled circuit is not covered and would need re-enumerating against the device graph.
All-to-all hardware avoids the issue.

## Working rules

1. No number enters the manuscript that a script did not produce.
2. No gate list is written by hand. Circuits are synthesized from a frame specification and
   verified twice by independent methods.
3. The decoder is an output of the fault enumeration, never an input to it.
4. Bounded searches log their bounds. A cap that is not logged reads as coverage.
5. "Approximately N gates" is banned vocabulary for a circuit that exists as a file.
6. **Every protection must be shown load-bearing by ablation.** Adding protections until a
   check passes is how gadgets become over-engineered, because nothing in that process says
   which addition did the work. Three were removed this way, saving 42 two-qubit gates and
   doubling the yield.
7. A control that cannot fail is not a control. Every certificate here ships with a
   deliberately crippled variant that does fail.
