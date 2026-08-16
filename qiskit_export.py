"""Export the certified protocol to Qiskit, and cross-check it on Aer.

The circuit is TRANSLATED from the same stim circuit the certificate is built on, not
rewritten by hand. A hand-written second copy would be a second thing to keep correct,
and the whole point of this repository is that there is one source per artifact.

Two facts make the port easy, and both are consequences of the protocol's design:

  * No dynamic circuits and no feed-forward. The Pauli frame update
    Xbar^(m2 + b5) Zbar^(m1) is classical bookkeeping applied to the final readout, not a
    conditional gate, so the circuit is static and the corrections are post-processing.
  * Detectors are parities of measurement bits. Qiskit has no detector concept, so each
    one becomes an index set over the shot bitstring; a shot is accepted when every
    detector parity is zero.

Noise is translated instruction by instruction into explicit Pauli error channels with
stim's exact probabilities: DEPOLARIZE1(p) puts p/3 on each of X, Y, Z, and DEPOLARIZE2(p)
puts p/15 on each of the fifteen non-identity two-qubit Paulis. Matching the noise model
is what makes the comparison a check on the translation rather than on the noise
conventions of two simulators.

Hardware note. The certificate covers THIS circuit. Transpiling onto a restricted coupling
map inserts SWAPs, each three CX gates that the fault enumeration never saw, so a
transpiled circuit is not covered and would need re-enumerating against the actual device
graph. All-to-all hardware avoids the issue entirely.
"""
import itertools
import json
import os
import sys

import numpy as np
import stim
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import pauli_error

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import end_to_end as E  # noqa: E402

PAULI2 = [a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II"]


def depol1(p):
    return pauli_error([("I", 1 - p), ("X", p / 3), ("Y", p / 3), ("Z", p / 3)])


def depol2(p):
    return pauli_error([("II", 1 - p)] + [(pp, p / 15) for pp in PAULI2])


def flip(p, pauli="X"):
    return pauli_error([("I", 1 - p), (pauli, p)])


def translate(stim_circuit, n_qubits):
    """stim -> (QuantumCircuit, detector index sets, observable index set).

    MPP is expanded into an ancilla cascade, since Qiskit has no joint-Pauli measurement.
    One shared ancilla suffices because every MPP resets it first."""
    mpp_anc = n_qubits
    total_q = n_qubits + 1
    insts = list(stim_circuit.flattened())

    def count_measurements(inst):
        """stim batches measurements: 'M q1 q2' is two, and one MPP holds one
        measurement per Pauli product, not one per target."""
        tg = inst.targets_copy()
        if inst.name in ("M", "MX", "MY"):
            return len(tg)
        if inst.name != "MPP":
            return 0
        n, i = 0, 0
        while i < len(tg):
            i += 1
            while i < len(tg) and tg[i].is_combiner:
                i += 2
            n += 1
        return n

    n_meas = sum(count_measurements(i) for i in insts)
    qc = QuantumCircuit(total_q, n_meas)
    m = 0
    detectors, observable = [], []

    def rec_to_abs(targets):
        return sorted(m + t.value for t in targets if t.is_measurement_record_target)

    for inst in insts:
        name = inst.name
        tg = inst.targets_copy()
        vals = [t.value for t in tg if not t.is_combiner]

        if name in ("H", "S", "S_DAG", "X", "Y", "Z", "I"):
            for q in vals:
                getattr(qc, {"H": "h", "S": "s", "S_DAG": "sdg", "X": "x", "Y": "y",
                             "Z": "z", "I": "id"}[name])(q)
        elif name in ("CX", "CY", "CZ"):
            for a, b in zip(vals[::2], vals[1::2]):
                getattr(qc, name.lower())(a, b)
        elif name == "R":
            for q in vals:
                qc.reset(q)
        elif name == "RX":
            for q in vals:
                qc.reset(q)
                qc.h(q)
        elif name in ("M", "MX"):
            p = inst.gate_args_copy()
            for q in vals:
                if p and p[0] > 0:
                    # stim flips the reported outcome; for an ancilla that is reset
                    # afterwards this is the same as flipping the qubit beforehand
                    qc.append(flip(p[0], "Z" if name == "MX" else "X").to_instruction(), [q])
                if name == "MX":
                    qc.h(q)
                qc.measure(q, m)
                m += 1
        elif name == "MPP":
            groups, cur = [], []
            i = 0
            while i < len(tg):
                cur = [tg[i]]
                i += 1
                while i < len(tg) and tg[i].is_combiner:
                    cur.append(tg[i + 1])
                    i += 2
                groups.append(cur)
            for grp in groups:
                qc.reset(mpp_anc)
                qc.h(mpp_anc)
                for t in grp:
                    q = t.qubit_value
                    if t.is_x_target:
                        qc.cx(mpp_anc, q)
                    elif t.is_y_target:
                        qc.cy(mpp_anc, q)
                    else:
                        qc.cz(mpp_anc, q)
                qc.h(mpp_anc)
                qc.measure(mpp_anc, m)
                m += 1
        elif name == "DEPOLARIZE1":
            p = inst.gate_args_copy()[0]
            for q in vals:
                qc.append(depol1(p).to_instruction(), [q])
        elif name == "DEPOLARIZE2":
            p = inst.gate_args_copy()[0]
            for a, b in zip(vals[::2], vals[1::2]):
                qc.append(depol2(p).to_instruction(), [a, b])
        elif name in ("X_ERROR", "Z_ERROR"):
            p = inst.gate_args_copy()[0]
            for q in vals:
                qc.append(flip(p, name[0]).to_instruction(), [q])
        elif name == "DETECTOR":
            detectors.append(rec_to_abs(tg))
        elif name == "OBSERVABLE_INCLUDE":
            observable.extend(rec_to_abs(tg))
        elif name in ("TICK", "QUBIT_COORDS", "SHIFT_COORDS"):
            continue
        else:
            raise NotImplementedError(f"no Qiskit translation for {name}")
    return qc, detectors, sorted(observable)


def postprocess(memory, detectors, observable, n_meas):
    """memory: list of Qiskit bitstrings, most significant bit = highest clbit index."""
    bits = np.array([[int(s[n_meas - 1 - i]) for i in range(n_meas)] for s in memory],
                    dtype=np.uint8)
    fired = np.zeros(len(bits), dtype=bool)
    for det in detectors:
        fired |= bits[:, det].sum(axis=1) % 2 == 1
    accepted = ~fired
    obs = bits[:, observable].sum(axis=1) % 2
    return accepted, obs


def detector_rates_aer(basis, p, shots, seed=7):
    circ = E.build(basis, p).c
    qc, detectors, observable = translate(circ, E.NQ)
    sim = AerSimulator(method="stabilizer", seed_simulator=seed)
    memory = sim.run(qc, shots=shots, memory=True).result().get_memory()
    n = qc.num_clbits
    bits = np.array([[int(s[n - 1 - i]) for i in range(n)] for s in memory], dtype=np.uint8)
    return np.array([bits[:, d].sum(axis=1) % 2 for d in detectors]).mean(axis=1)


def detector_rates_stim(basis, p, shots, seed=7):
    circ = E.build(basis, p).c
    det, _ = circ.compile_detector_sampler(seed=seed).sample(
        shots, separate_observables=True)
    return det.mean(axis=0)


def run(basis, p, shots, seed=1234):
    circ = E.build(basis, p).c
    qc, detectors, observable = translate(circ, E.NQ)
    sim = AerSimulator(method="stabilizer", seed_simulator=seed)
    result = sim.run(qc, shots=shots, memory=True).result()
    memory = result.get_memory()
    accepted, obs = postprocess(memory, detectors, observable, qc.num_clbits)
    return qc, int(accepted.sum()), int(obs[accepted].sum()), len(detectors)


if __name__ == "__main__":
    SHOTS = int(sys.argv[1]) if len(sys.argv) > 1 else 40000

    qc, _, _, ndet = run("Z", 0.0, 200)
    print(f"translated circuit: {qc.num_qubits} qubits, {qc.num_clbits} measurements, "
          f"{ndet} detectors, depth {qc.depth()}")
    counts = qc.count_ops()
    n2 = sum(v for k, v in counts.items() if k in ("cx", "cy", "cz"))
    print(f"   two-qubit gates {n2} (stim circuit reports "
          f"{sum(len(i.targets_copy()) // 2 for i in E.build('Z', 0.0).c.flattened() if i.name in ('CX', 'CY', 'CZ'))}"
          f", plus the MPP expansions Qiskit needs)")

    print("\nnoiseless sanity check (Aer)")
    for basis in ("X", "Z"):
        _, acc, err, _ = run(basis, 0.0, 400)
        print(f"   prep {basis}bar: accepted {acc}/400, logical errors {err}")
        assert acc == 400 and err == 0, "noiseless protocol is not deterministic in Aer"

    print("\nper-detector firing rates, Aer against stim, 20,000 shots at p = 0.005")
    print("   (43 common events; a miswired detector shows up here, not in acceptance)")
    worst_det = 0.0
    for basis in ("X", "Z"):
        a = detector_rates_aer(basis, 0.005, 20000)
        s_ = detector_rates_stim(basis, 0.005, 20000)
        diff = np.abs(a - s_)
        worst_det = max(worst_det, float(diff.max()))
        print(f"   prep {basis}bar: {len(a)} detectors, mean rate "
              f"{a.mean():.4f} vs {s_.mean():.4f}, largest per-detector gap "
              f"{diff.max():.4f} at detector {int(diff.argmax())}")
    tol = 4 * (0.5 / 20000 ** 0.5)
    print(f"   largest gap {worst_det:.4f} against a 4-sigma shot-noise band of {tol:.4f}: "
          f"{'consistent' if worst_det < tol else 'DISCREPANT'}")

    with open(os.path.join(ROOT, "results", "numerics.json")) as fh:
        stim_rows = {r["p"]: r for r in json.load(fh)["certified"]["rows"]}

    print(f"\ncross-check against stim, {SHOTS:,} shots per point")
    print(f"{'p':>8} {'aer accept':>12} {'stim accept':>12} {'aer p_L':>11} {'stim p_L':>11}")
    out = []
    for p in (0.003, 0.005, 0.01):
        acc_tot = err_tot = 0
        for basis in ("X", "Z"):
            _, a, e, _ = run(basis, p, SHOTS // 2)
            acc_tot += a
            err_tot += e
        aer_acc = acc_tot / SHOTS
        aer_pl = err_tot / acc_tot if acc_tot else float("nan")
        s = stim_rows[p]
        print(f"{p:8.3f} {aer_acc:12.4f} {s['acceptance']:12.4f} "
              f"{aer_pl:11.2e} {s['p_logical']:11.2e}")
        out.append({"p": p, "aer_acceptance": aer_acc, "stim_acceptance": s["acceptance"],
                    "aer_p_logical": aer_pl, "stim_p_logical": s["p_logical"],
                    "aer_accepted": acc_tot, "aer_errors": err_tot})
    json.dump(out, open(os.path.join(ROOT, "results", "qiskit_crosscheck.json"), "w"),
              indent=2)
    worst = max(abs(r["aer_acceptance"] - r["stim_acceptance"]) for r in out)
    print(f"\nlargest acceptance discrepancy: {worst:.4f}")
    print("Acceptance is the sharp comparison: it is order one, so a translation error "
          "would show up\nimmediately. The logical rate is rarer and noisier at these "
          "shot counts.")
