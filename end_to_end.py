"""Step 7: end-to-end single-fault enumeration over the whole teleportation switch.

Each gadget now has its own certificate. Certificates do not compose for free: an error
left on B by its own verification round is harmless while B sits idle and becomes a data
error the moment M1 couples to it. Only one enumeration over the whole protocol catches
that, and building it with the measurement rounds in place also settles the correlated
case, where a single fault both flips an M1 outcome and leaves a data error. That stops
being a separate argument and becomes one more fault location.

Formulation. The protocol is built as a stim circuit with a DETECTOR for every
post-selection check (A's input syndromes, B's verification syndromes, every flag, the
agreement of the repeated M1 rounds, and the ZZZZ parity of A's destructive readout) and
an OBSERVABLE_INCLUDE for the teleported logical, combined with the frame bits. Noise is
attached only to the protocol's own gates: block A arrives as given (its input errors are
out of scope by Lemma 1) and the final logical readout is a verification device, so both
are noiseless.

A single fault is DANGEROUS exactly when it flips the observable while firing no
detector. Stim's detector error model lists every fault mechanism with its detectors and
observable flips, so the check is a scan of that model rather than a hand argument.
"""
import json
import sys

import stim

import frames as F
from frames import ps

A = [0, 1, 2, 3]
B = [4, 5, 6, 7, 8]
ANC_A = [9, 10]
ANC_BV, FLG_BV = [11, 12, 13, 14], [15, 16, 17, 18]
ANC_ZB, FLG_ZB = 19, 26
# r = 3. r = 1 fails outright: with one round there is no round-to-round detector to
# catch a measurement flip. r = 2 certifies and is cheaper in gates and yield, but
# tune_protocol.py shows it costs a factor of three in logical error rate, which is the
# wrong thing to trade away in a factory whose product is a low-error encoded state.
ROUNDS = 3
ANC_M1 = [20, 21, 22]
FLG_M1 = [23, 24, 25]
FLG_A = [27, 28]
NQ = 29

A_X1, A_Z1, A_Z2 = "XXII", "ZIZI", "ZZII"
P = {"X": stim.target_x, "Y": stim.target_y, "Z": stim.target_z}


class Builder:
    def __init__(self, noise=0.0):
        self.c = stim.Circuit()
        self.n = 0            # measurements so far
        self.noise = noise
        self.rec = {}
        self.det_labels = []   # one stage label per detector, for yield attribution

    def mpp(self, name, spec):
        t = []
        for i, (q, pauli) in enumerate(spec):
            if i:
                t.append(stim.target_combiner())
            t.append(P[pauli](q))
        self.c.append("MPP", t)
        self.rec[name] = self.n
        self.n += 1

    def gate(self, name, targets, noisy=True):
        self.c.append(name, targets)
        if noisy and self.noise:
            if name in ("CX", "CY", "CZ"):
                self.c.append("DEPOLARIZE2", targets, self.noise)
            elif name in ("H", "S"):
                self.c.append("DEPOLARIZE1", targets, self.noise)

    def reset(self, name, targets, noisy=True):
        self.c.append(name, targets)
        if noisy and self.noise:
            self.c.append("Z_ERROR" if name == "RX" else "X_ERROR", targets, self.noise)

    def measure(self, name, basis, q, noisy=True):
        if noisy and self.noise:
            self.c.append("MX" if basis == "X" else "M", [q], self.noise)
        else:
            self.c.append("MX" if basis == "X" else "M", [q])
        self.rec[name] = self.n
        self.n += 1

    def detector(self, names, stage="unlabelled"):
        self.c.append("DETECTOR", [stim.target_rec(self.rec[x] - self.n) for x in names])
        self.det_labels.append(stage)

    def observable(self, names, index=0):
        self.c.append("OBSERVABLE_INCLUDE",
                      [stim.target_rec(self.rec[x] - self.n) for x in names], index)

    def measure_pauli(self, name, spec, anc, flag=None, bracket=None, noisy=True):
        """Ancilla cascade measuring a Pauli product, optionally flag protected."""
        self.reset("RX", [anc], noisy)
        if flag is not None:
            self.reset("R", [flag], noisy)
        for slot in range(len(spec) + 1):
            if flag is not None and bracket and slot == bracket[0]:
                self.gate("CX", [anc, flag], noisy)
            if slot < len(spec):
                q, pauli = spec[slot]
                self.gate({"X": "CX", "Y": "CY", "Z": "CZ"}[pauli], [anc, q], noisy)
            if flag is not None and bracket and slot == bracket[1]:
                self.gate("CX", [anc, flag], noisy)
        self.measure(name, "X", anc, noisy)
        if flag is not None:
            self.measure(name + "_flag", "Z", flag, noisy)


def on(block, pauli_string):
    return [(block[i], ch) for i, ch in enumerate(pauli_string) if ch != "I"]


PREP_B = stim.Circuit("""
    RX 0 1 2 3 4
""")


def prep_b_ops():
    """Graph-state preparation of |0>_L, from prep_factory: 6 two-qubit gates."""
    zs = [ps(F.OUT_Z)] + [ps(s) for s in F.OUT_STAB]
    xs = F.symplectic_completion(zs)
    T = stim.Tableau.from_conjugated_generators(xs=xs, zs=zs)
    circ = T.to_circuit(method="graph_state")
    resets, ops = {}, []
    for inst in circ.flattened():
        tg = [t.value for t in inst.targets_copy()]
        if inst.name in ("R", "RX", "RY", "RZ"):
            for q in tg:
                resets[q] = inst.name
            continue
        if inst.name in ("CX", "CY", "CZ", "SWAP"):
            for a, b in zip(tg[::2], tg[1::2]):
                ops.append((inst.name, [a, b]))
        else:
            for q in tg:
                ops.append((inst.name, [q]))
    return resets, ops


B_RESETS, B_OPS = prep_b_ops()


def build(prep_basis, noise=0.0, cripple=None, m1_rounds=None,
          zbar_rounds=None):
    """cripple: a protection name, or a collection of them, to remove. Used by
    validate_certificate.py to check that each protection is load-bearing."""
    off = set()
    if cripple is not None:
        off = {cripple} if isinstance(cripple, str) else set(cripple)

    class _C:
        def __eq__(self, other):
            return other in off

        def __ne__(self, other):
            return other not in off

    cripple = _C()
    m1_rounds = ROUNDS if m1_rounds is None else m1_rounds
    zbar_rounds = ROUNDS if zbar_rounds is None else zbar_rounds
    b = Builder(noise)

    # --- input block A, given, noiseless (Lemma 1 puts its errors out of scope) -----
    b.mpp("a_xxxx0", on(A, "XXXX"))
    b.mpp("a_zzzz0", on(A, "ZZZZ"))
    b.mpp("a_z2", on(A, A_Z2))
    b.mpp("a_log", on(A, A_X1 if prep_basis == "X" else A_Z1))

    # --- step 1: verify A, post-select ----------------------------------------------
    # flag protected: an unflagged cascade spreads ancilla errors across A, and an
    # even-weight X error on A slips past the ZZZZ readout check while still flipping M2
    # One round only. A second round was carried for a while and ablation showed it to be
    # pure cost: removing it leaves the certificate intact and raises the yield. The Z
    # error it was meant to catch is caught by the XXXX checks interleaved into step 3.
    for r in range(1):
        b.measure_pauli(f"a_xxxx{r}v", on(A, "XXXX"), ANC_A[0],
                        None if cripple == "a_flag" else FLG_A[0],
                        None if cripple == "a_flag" else (0, 4))
        b.measure_pauli(f"a_zzzz{r}v", on(A, "ZZZZ"), ANC_A[1],
                        None if cripple == "a_flag" else FLG_A[1],
                        None if cripple == "a_flag" else (0, 4))
        for tag in (f"a_xxxx{r}v", f"a_zzzz{r}v"):
            if cripple != "a_flag":
                b.detector([tag + "_flag"], "A verify")
        b.detector(["a_xxxx0", f"a_xxxx{r}v"], "A verify")
        b.detector(["a_zzzz0", f"a_zzzz{r}v"], "A verify")

    # --- step 2: prepare B and verify it ---------------------------------------------
    for q, kind in B_RESETS.items():
        b.reset(kind, [B[q]])
    for name, tg in B_OPS:
        b.gate(name, [B[q] for q in tg])
    def verify_b(tag, noisy=True):
        for i, g in enumerate(F.OUT_STAB):
            b.measure_pauli(f"b_g{i}_{tag}", on(B, g), ANC_BV[i], FLG_BV[i], (0, 4),
                            noisy=noisy)
            b.detector([f"b_g{i}_{tag}"], "B verify")
            if noisy:
                b.detector([f"b_g{i}_{tag}_flag"], "B verify")

    verify_b("r0")
    # The Zbar frame bit is recorded AFTER verification, per the prep_factory ordering
    # rule. Its own cascade must therefore be flagged and repeated, and a second
    # verification round has to follow it: errors this cascade injects into B would
    # otherwise face no further check before M1 couples to the block.
    # Repetition is load-bearing here; a flag on this cascade is not, and neither is a
    # second B verification round after it. Both were carried and both were shown by
    # ablation to cost gates and yield while changing nothing.
    for r in range(1 if cripple == "zbar_repeat" else zbar_rounds):
        b.measure_pauli(f"b_zbar_{r}", on(B, F.OUT_Z), ANC_ZB)
        if r:
            b.detector([f"b_zbar_{r-1}", f"b_zbar_{r}"], "Zbar repeat")

    # --- step 3: joint logical measurement, repeated --------------------------------
    spec = on(A, A_X1) + on(B, F.OUT_X)
    use_flag = cripple != "m1_flag"
    for r in range(m1_rounds):
        b.measure_pauli(f"m1_{r}", spec, ANC_M1[r % len(ANC_M1)],
                        FLG_M1[r % len(FLG_M1)] if use_flag else None,
                        (0, len(spec)) if use_flag else None)
        if use_flag:
            b.detector([f"m1_{r}_flag"], "M1 flag")
        if r:
            b.detector([f"m1_{r-1}", f"m1_{r}"], "M1 repeat")
        if r < m1_rounds - 1 and cripple != "a_interleave":
            # Interleaved XXXX check on A. A Z error landing on q1 or q2 during an M1
            # cascade flips the M1 outcome in EVERY later round identically, so the
            # round-to-round detectors cannot see it. It anticommutes with XXXX, so an
            # interleaved check does.
            b.measure_pauli(f"a_xxxx_m{r}", on(A, "XXXX"), ANC_A[0], FLG_A[0], (0, 4))
            b.detector([f"a_xxxx_m{r}_flag"], "A interleave")
            b.detector(["a_xxxx0", f"a_xxxx_m{r}"], "A interleave")

    # --- step 3b: hand-off EC round on B --------------------------------------------
    # Errors injected into B by the M1 cascades face no further check otherwise. This
    # round is NOISELESS by convention: it stands for the receiving computation's own
    # first error-correction cycle, which is where a real switch hands the block over.
    if cripple != "handoff":
        verify_b("final", noisy=False)

    # --- step 4: read A out destructively; ZZZZ parity is a free check ---------------
    for i, q in enumerate(A):
        b.measure(f"a_out{i}", "Z", q)
    b.detector(["a_zzzz0", "a_out0", "a_out1", "a_out2", "a_out3"], "A readout")

    # --- step 5: verify the teleported logical, noiseless ----------------------------
    b.mpp("out", on(B, F.OUT_X if prep_basis == "X" else F.OUT_Z))
    if prep_basis == "X":
        b.observable(["out", "a_log", "m1_0"])
    else:
        b.observable(["out", "a_log", "b_zbar_0", "a_out0", "a_out2"])
    return b


def check_noiseless(prep_basis):
    b = build(prep_basis, 0.0)
    sampler = b.c.compile_detector_sampler()
    det, obs = sampler.sample(2048, separate_observables=True)
    return int(det.sum()), int(obs.sum()), b


print("Noiseless protocol: every detector must be silent and the observable must be 0\n")
ok = True
for basis in ("X", "Z"):
    ndet, nobs, b = check_noiseless(basis)
    n_detectors = b.c.num_detectors
    print(f"  prep {basis}bar: {n_detectors} detectors, {b.n} measurements, "
          f"detector firings {ndet}, observable flips {nobs}")
    ok &= (ndet == 0 and nobs == 0)
if not ok:
    print("\nProtocol bookkeeping is wrong; not proceeding to the fault scan.")
    sys.exit(1)
print("\nBookkeeping verified: the protocol is deterministic and the frame is correct.\n")

print("=" * 74)
print("End-to-end single-fault scan")
print("=" * 74)
summary = {}
for basis in ("X", "Z"):
    b = build(basis, 1e-3)
    dem = b.c.detector_error_model(decompose_errors=False, allow_gauge_detectors=True)
    n_mech = dangerous = 0
    examples = []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        n_mech += 1
        dets = [t for t in inst.targets_copy() if t.is_relative_detector_id()]
        obs = [t for t in inst.targets_copy() if t.is_logical_observable_id()]
        if obs and not dets:
            dangerous += 1
            if len(examples) < 5:
                examples.append(str(inst))
    print(f"  prep {basis}bar: {n_mech} single-fault mechanisms, "
          f"{dangerous} flip the observable with NO detector")
    for e in examples:
        print(f"     {e}")
    summary[basis] = {"mechanisms": n_mech, "dangerous": dangerous}

# --- positive control: the scan must be able to FAIL ---------------------------
def scan(circuit):
    dem = circuit.detector_error_model(decompose_errors=False, allow_gauge_detectors=True)
    bad = 0
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        t = inst.targets_copy()
        if (any(x.is_logical_observable_id() for x in t)
                and not any(x.is_relative_detector_id() for x in t)):
            bad += 1
    return bad


n_ctrl = scan(build("Z", 1e-3, cripple="m1_flag").c)
print(f"\npositive control: removing the M1 flag entirely yields {n_ctrl} dangerous "
      f"mechanism(s). The scan can fail, so a clean result means something.")
assert n_ctrl > 0, "positive control did not fail; the scan may be vacuous"

# --- resources, counted from the circuit -----------------------------------------
noiseless = build("Z", 0.0).c
n2 = sum(len(i.targets_copy()) // 2 for i in noiseless.flattened()
         if i.name in ("CX", "CY", "CZ"))
print(f"\ntwo-qubit gates in the full protocol, counted from the circuit: {n2}")
print("   (includes the noiseless hand-off EC round, which a real switch charges to the")
print("    receiving computation rather than to the switch)")

total_bad = sum(v["dangerous"] for v in summary.values())
print(f"\n=> {'FAULT TOLERANT end to end' if total_bad == 0 else 'NOT fault tolerant'}: "
      f"{total_bad} undetectable single-fault logical errors")
summary["two_qubit_gates"] = n2
summary["positive_control_dangerous"] = n_ctrl
json.dump(summary, open("results/end_to_end.json", "w"), indent=2)
