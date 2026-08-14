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
25 CX) and 97,466 valid single-flag designs, none certifies Phase 3. The best leaves 14
of 16 buckets mixing logically inequivalent residuals. This closes the
"one or two bracketing-pair flags" family and forces a different Phase 3 structure.
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
