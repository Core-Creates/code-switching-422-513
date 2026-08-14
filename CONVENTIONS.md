# CONVENTIONS.md - single source of truth

Everything (code, figures, tables, LaTeX) draws from this file. If a statement in the
manuscript disagrees with this file, the manuscript is wrong.

## Qubit indexing

- Physical qubits are `q1..q5` in prose, `0..4` in code (0-based, `qN` == index `N-1`).
- Pauli strings are written left-to-right as `q1 q2 q3 q4 q5`.
  `XZZXI` means X on q1, Z on q2, Z on q3, X on q4, I on q5.
- Stim little-endian: qubit index 0 is the least significant bit of a basis state.
- Ancillas are never numbered in the same namespace as data qubits.

## Gate conventions

- `CNOT(a -> b)`: control a, target b. In stim: `CX a b`.
- Error propagation through `CNOT(a -> b)`: X on control -> X on control and target.
  Z on target -> Z on target and control. (Forward for X, backward for Z.)
- `CZ(a,b)` is symmetric. `S = diag(1, i)`. `H` is the standard Hadamard.

## [[4,2,2]] code (source)

- Stabilizers: `S1 = XXXX`, `S2 = ZZZZ`.
- Logical qubit 1 (KEPT):      `X1bar = XXII`, `Z1bar = ZIZI`
- Logical qubit 2 (SACRIFICED): `X2bar = XIXI`, `Z2bar = ZZII`

  Z2bar IS `ZZII`. It is NOT `ZIZI`. `ZIZI` is Z1bar, the logical operator we keep.
  Measuring `ZIZI` destroys the payload. Any circuit that realizes the Phase 2
  measurement with controls on q1 and q3 is measuring Z1bar and is WRONG; the
  correct parity measurement has controls on q1 and q2.

## Phase 2 post-measurement frame (the encoder's INPUT frame)

After measuring Z2bar = ZZII with outcome m in {0,1} and adjoining a fresh q5 in |0>,
on 5 qubits:

- Stabilizers: `XXXXI`, `(-1)^m ZZIII`, `IIZZI`, `IIIIZ`
- Logicals:    `Xbar_in = XXIII`, `Zbar_in = ZIZII`

The m=1 branch is handled by a Pauli frame update, not by a different circuit.
The frame-fixing operator is computed in `synthesize_encoder.py` (it must anticommute
with ZZIII and commute with the other three stabilizers and with both logicals).

## [[5,1,3]] code (target)

- Stabilizers: `g1 = XZZXI`, `g2 = IXZZX`, `g3 = XIXZZ`, `g4 = ZXIXZ`
- Logicals: `Xbar = XXXXX`, `Zbar = ZZZZZ`
- Syndrome bit order: `(s1,s2,s3,s4)` = eigenvalues of `(g1,g2,g3,g4)`,
  with `s_i = 0` for eigenvalue +1 and `s_i = 1` for eigenvalue -1.

## The encoder U

`U` is a Clifford on 5 qubits defined by frame-to-frame mapping, NOT by a hand-picked
gate list:

    U XXXXI U+ = g1 = XZZXI      U XXIII U+ = XXXXX
    U ZZIII U+ = g2 = IXZZX      U ZIZII U+ = ZZZZZ
    U IIZZI U+ = g3 = XIXZZ
    U IIIIZ U+ = g4 = ZXIXZ

(The assignment of input stabilizers to output generators is a choice; any bijection
that preserves commutation works. This one is fixed here so the code and the paper
agree.) The gate list is synthesized from this specification and re-derived by script;
no gate is ever typed by hand into the manuscript.

## Banned vocabulary

"approximately N gates", "about N CNOTs", "~15", "20-25 layers" for any circuit that
exists as a file. Counts are integers read off the circuit.
