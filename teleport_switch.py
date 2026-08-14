"""Teleportation-based [[4,2,2]] -> [[5,1,3]] switch.

Step 4 closed the flag-protected re-encoding route: a counting bound forces at least 2
flag bits, no pair of flags covers the separation constraints, and a greedy cover needs
9. This is the alternative Section 6.2 dismissed on a resource comparison against a
baseline that was understated fivefold.

PROTOCOL (one-bit teleportation by joint logical measurement, no cross-code CNOT):

  1. verify block A, the [[4,2,2]] block, by measuring XXXX and ZZZZ and post-selecting
  2. prepare block B, a fresh [[5,1,3]] block, in |0>_L and verify it
  3. measure the joint logical operator M1 = X1bar_A (x) Xbar_B = XXII (x) XXXXX
  4. measure M2 = Z1bar_A = ZIZI, which measures block A out
  5. Pauli frame update on B: Xbar^(m2 + b5) Zbar^(m1)

Three structural advantages over re-encoding, and they are the reason to expect this
route to certify where the other could not:

  * Block A is destroyed. A fault on A can only corrupt a classical outcome, which
    repetition handles; it cannot corrupt the output state. In the re-encoding route
    every data qubit of A became a data qubit of the output.
  * Phase 2 disappears. There is no need to measure Z2bar first: the second logical
    qubit is discarded with the block. That removes the step that carried defect 1.
  * The only object needing fault-tolerant protection is a Pauli product measurement,
    which is exactly what flag gadgets were designed for, rather than an encoding
    cascade, which is what they failed on.

Lemma 1 is unaffected: errors already on A before the switch remain uncorrectable, so
step 1's post-selection stays load-bearing and the scope stays a state-preparation
factory.

This file verifies the IDEAL protocol. Fault tolerance of the weight-7 measurement is
the next step and is not claimed here.
"""
import numpy as np
import stim

import frames as F
from frames import ps

A = [0, 1, 2, 3]        # [[4,2,2]] block, q1..q4
B = [4, 5, 6, 7, 8]     # [[5,1,3]] block, b1..b5

A_STAB = ["XXXX", "ZZZZ"]
A_X1, A_Z1 = "XXII", "ZIZI"     # kept logical qubit
A_Z2 = "ZZII"                   # discarded logical qubit


def targets(spec):
    """spec: list of (qubit, pauli). Returns MPP targets with combiners."""
    out = []
    for i, (q, p) in enumerate(spec):
        if i:
            out.append(stim.target_combiner())
        out.append({"X": stim.target_x, "Y": stim.target_y, "Z": stim.target_z}[p](q))
    return out


def on(block, pauli_string):
    return [(block[i], c) for i, c in enumerate(pauli_string) if c != "I"]


def build(prep_basis):
    """prep_basis 'Z' prepares logical |0>/|1> on A, 'X' prepares |+>/|->.
    Returns (circuit, record index map)."""
    c = stim.Circuit()
    c.append("R", A + B)
    rec = {}
    order = []

    def measure(name, spec):
        c.append("MPP", targets(spec))
        order.append(name)
        rec[name] = len(order) - 1

    # 1. project A into the [[4,2,2]] code and fix both logical qubits
    measure("a_xxxx", on(A, A_STAB[0]))
    measure("a_zzzz", on(A, A_STAB[1]))
    measure("a_z2", on(A, A_Z2))
    measure("a_log", on(A, A_X1 if prep_basis == "X" else A_Z1))

    # 2. project B into the [[5,1,3]] code, in a Zbar eigenstate
    for i, g in enumerate(F.OUT_STAB):
        measure(f"b_g{i+1}", on(B, g))
    measure("b_zbar", on(B, F.OUT_Z))

    # 3. joint logical measurement, weight 7
    measure("m1", on(A, A_X1) + on(B, F.OUT_X))

    # 4. measure block A out
    measure("m2", on(A, A_Z1))

    # 5. read the teleported logical out of B
    measure("out", on(B, F.OUT_X if prep_basis == "X" else F.OUT_Z))
    return c, rec, order


def check(prep_basis, shots=4096):
    c, rec, order = build(prep_basis)
    data = c.compile_sampler().sample(shots)
    if prep_basis == "X":
        # Xbar_B picks up a sign from the Zbar^m1 frame Pauli
        combo = ["out", "a_log", "m1"]
    else:
        # Zbar_B picks up a sign from the Xbar^(m2+b5) frame Pauli
        combo = ["out", "a_log", "m2", "b_zbar"]
    parity = np.zeros(shots, dtype=bool)
    for k in combo:
        parity ^= data[:, rec[k]]
    n_bad = int(parity.sum())
    print(f"  prep {prep_basis}bar: parity of {combo} is "
          f"{'DETERMINISTIC 0' if n_bad == 0 else f'NOT deterministic ({n_bad}/{shots})'}")
    rand = {k: float(data[:, rec[k]].mean()) for k in ("m1", "m2", "a_log")}
    print(f"     individual outcomes are random as expected: "
          + ", ".join(f"{k}={v:.2f}" for k, v in rand.items()))
    return n_bad == 0


print("Ideal-protocol verification (MPP model, no noise)")
ok_x = check("X")
ok_z = check("Z")
assert ok_x and ok_z, "teleportation identity failed"
print("\nBoth logical operators teleport: Xbar_A -> Xbar_B and Zbar_A -> Zbar_B, with the")
print("frame Pauli Xbar^(m2 + b5) Zbar^(m1) as derived.")

# ---------------------------------------------------------------- resources
print("\n" + "=" * 74)
print("Resource comparison, exact two-qubit gate counts")
print("=" * 74)


def prep_zero_L_circuit():
    """A Clifford V with V|00000> = |0>_L for [[5,1,3]], synthesized from the frame the
    same way the re-encoder was: never a hand-written gate list."""
    zs = [ps(F.OUT_Z)] + [ps(s) for s in F.OUT_STAB]
    xs = F.symplectic_completion(zs)
    V = stim.Tableau.from_conjugated_generators(xs=xs, zs=zs)
    circ = V.to_circuit(method="elimination")
    T = stim.Tableau.from_circuit(circ)
    assert T(ps("ZIIII")) == ps(F.OUT_Z)
    for i, g in enumerate(F.OUT_STAB):
        assert T(ps("I" * (i + 1) + "Z" + "I" * (3 - i))) == ps(g)
    return circ


prep = prep_zero_L_circuit()
n_prep = sum(len(i.targets_copy()) // 2 for i in prep.flattened() if i.name == "CX")
print(f"[[5,1,3]] |0>_L preparation, synthesized and verified: {n_prep} CX")

r = 3
tele = [
    ("verify A: measure XXXX and ZZZZ", 4 + 4),
    ("prepare B in |0>_L (unoptimized)", n_prep),
    ("verify B preparation (one flag ancilla, 2 couplings)", 2),
    (f"joint M1 = XXII (x) XXXXX, weight 7, r={r}", 7 * r),
    ("measure A out: M2 = ZIZI", 2),
]
flagroute = [
    ("Phase 0: measure XXXX and ZZZZ", 8),
    ("Phase 1: ancilla verification", 1),
    ("Phase 2: measure Z2bar", 2),
    ("Phase 3: verified re-encoder", 17),
    ("Phase 3: flag coupling as described in the draft", 3),
    (f"Phase 4: four weight-4 generators, r={r}", 4 * 4 * r),
]
for name, rows in (("teleportation switch", tele), ("flag re-encoding switch", flagroute)):
    tot = 0
    print(f"\n{name}:")
    for label, n in rows:
        tot += n
        print(f"   {label:56s} {n:4d}")
    print(f"   {'TOTAL':56s} {tot:4d}")

t_tot = sum(n for _, n in tele)
f_tot = sum(n for _, n in flagroute)
print(f"\nteleportation {t_tot} vs flag re-encoding {f_tot} two-qubit gates.")
print("Qubits: 4 (A) + 5 (B) + 1 measurement ancilla + flags, against 5 + 4 + 1 for the")
print("re-encoding route, whose flag budget the counting bound pushes toward 9.")
print("\nNote what is NOT yet counted for the teleportation route: whatever protection the")
print("weight-7 joint measurement needs. That is the next step, and it is the one that")
print("decides the comparison.")
