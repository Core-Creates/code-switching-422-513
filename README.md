# code-switching-422-513

Verified artifacts for fault-tolerant code switching from the [[4,2,2]] error-detecting
code to the [[5,1,3]] perfect code.

The manuscript is generated from this repo, not the other way round. Every circuit,
every syndrome, every gate count and every table entry is produced by a script and
checked by a test. Nothing is typed by hand into the paper.

## Layout

| path | what it is |
|---|---|
| `CONVENTIONS.md` | single source of truth: qubit order, gate direction, logical operator assignment, syndrome bit order |
| `frames.py` | the two stabilizer frames and the symplectic completion used to build tableaux |
| `synthesize_encoder.py` | Step 1: derives the re-encoding Clifford and verifies it two independent ways |
| `encoder.stim` | the derived encoder, 17 CX / 12 H / 15 S, unoptimized |
| `audit_paper_claims.py` | checks every load-bearing number in the draft manuscript |
| `flagsearch.py` | arity-generic fault enumeration, flag validation, decoder synthesis |
| `step2_flag_search.py` | Step 2: exhaustive flag placement search over one cascade |
| `step2_encoder_sweep.py` | Step 2 outer loop: resynthesize the cascade and rerun, all 24 bijections |
| `results/sweep_rows.jsonl` | per-cascade sweep results |
| `FINDINGS.md` | the audit: 16 numbered manuscript defects, Lemma 1, and the Step 2 result |
| `tests/` | pytest suite pinning all of the above |

## Quick start

    pip install -r requirements.txt
    pytest                  # 56 fast tests, under a second
    pytest -m slow          # adds the exhaustive single-flag search, a few minutes

    python synthesize_encoder.py     # rebuild and re-verify encoder.stim
    python audit_paper_claims.py     # print the manuscript audit
    python step2_flag_search.py      # flag search over the default cascade
    python step2_encoder_sweep.py    # sweep all 24 cascades (resumable)

## Results so far

**Step 1 is done.** The encoder is derived by frame composition rather than guessed,
and passes two independent verifications: exact conjugation of all six frame generators
including signs, and a raw statevector check with leakage 1.78e-15 and overlap 1.000000
onto the target codewords for both logical states. Exact resources: 17 CX, 12 H, 15 S.

**Lemma 1.** Twelve of the fifteen weight-one errors present on the data block when
Phase 3 begins lie in a confusable pair, so no encoder and no decoder can correct them.
At most three are correctable, and three is achieved by a synthesized decoder. Phase 0's
post-selection is therefore load-bearing, and the protocol is a state-preparation
factory unless discard-and-restart is replaced by frame updates.

**Step 2 is a negative result.** Across all 24 stabilizer bijections (cascades of 15 to
25 CX) and 97,466 valid single-flag designs, none certifies Phase 3.

**Steps 3 and 4 explain why, and close the flag approach.** A counting bound settles it
without any search: partition the Phase 3 faults by syndrome, and every one of the 16
classes holds 3 or 4 logically inequivalent residuals. A decoder keyed on
(syndrome, flag) splits each class into at most `2^b` groups, so at least 2 flag bits are
necessary wherever the couplings go. The manuscript's single flag carries one bit where
two are needed. Widening the family to three- and four-coupling flags across different
data qubits (17,287 valid designs, exhaustive at sizes 2 and 3) still certifies nothing,
exactly as the bound predicts. Recasting two-bit designs as exact set cover over 2,405
separation constraints and 1,706 distinct coverage patterns finds no covering pair at
all, and a greedy cover needs 9 flag bits. The gap between a lower bound of 2 and a
greedy cover of 9 puts flag-protected re-encoding well past the cost of the
teleportation-based switch that Section 6.2 dismisses.

See FINDINGS.md for what this does and does not establish.

## Fault model

Stated once, here and in `step2_flag_search.py`, and never restated informally.

Every gate of arity `k` contributes all `4^k - 1` non-identity Paulis on its support,
applied immediately after the gate, so correlated multi-qubit faults are covered for any
`k`. Preparation faults on the fresh `q5` and on each flag ancilla. A classical flip of
each flag readout. Optionally, idle faults on every qubit at every slot. Faults acting
trivially on a fresh ancilla are excluded as unphysical. Errors already present when
Phase 3 begins are out of scope by Lemma 1. Phase 4 is assumed ideal and carries its own
certificate.

Arity comes from Stim's gate metadata, with an override hook for gates Stim does not
model natively (CCZ, CCX, Molmer-Sorensen). `MPP` parity measurements become one
location spanning the whole Pauli product, and consecutive gates can be fused into an
atomic macro location for hardware whose native multi-qubit gate fails as a unit. Any
weight restriction is reported by `fault_model_summary`, never applied silently.

## Working rules

1. No number enters the manuscript that a script did not produce.
2. No gate list is written by hand. Circuits are synthesized from a frame specification
   and verified twice by independent methods.
3. The decoder is an output of the fault enumeration, never an input to it.
4. Bounded searches log their bounds. A cap that is not logged reads as coverage.
5. "Approximately N gates" is banned vocabulary for a circuit that exists as a file.

## Running it on Qiskit

    python qiskit_export.py

`qiskit_export.py` translates the certified stim circuit into a `QuantumCircuit` rather
than reimplementing it, so there is no second copy to keep correct. Two properties of the
protocol make the port straightforward:

- **No feed-forward.** The Pauli frame update is classical bookkeeping applied to the
  final readout, not a conditional gate, so the exported circuit is static. A test asserts
  that no conditional operation appears. This matters on hardware where dynamic circuits
  are slow or restricted.
- **Detectors become bit parities.** Qiskit has no detector concept, so each becomes an
  index set over the shot bitstring; a shot is accepted when all 43 parities are zero.

Noise is translated instruction by instruction with stim's exact probabilities, so the
Aer comparison tests the translation rather than two simulators' noise conventions.

Cross-check results: the noiseless protocol is deterministic in Aer in both logical bases;
all 43 per-detector firing rates agree with stim within shot noise (largest gap 0.0071
against a 4-sigma band of 0.0141); and acceptance agrees, landing at 0.7 sigma at 120,000
shots.

**Hardware caveat.** The certificate covers this circuit. Transpiling onto a restricted
coupling map inserts SWAPs, three CX gates apiece that the fault enumeration never saw, so
a transpiled circuit is not covered and would need re-enumerating against the device
graph. All-to-all hardware avoids the issue.
