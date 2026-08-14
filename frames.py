"""Code frames from CONVENTIONS.md. Nothing else in the repo hard-codes a Pauli."""
import itertools
import stim

# --- [[4,2,2]] source code, padded to 5 qubits with fresh q5 in |0> -----------
IN_STAB = ["XXXXI", "ZZIII", "IIZZI", "IIIIZ"]
IN_X = "XXIII"   # X1bar of [[4,2,2]]
IN_Z = "ZIZII"   # Z1bar of [[4,2,2]]

# --- [[5,1,3]] target code ---------------------------------------------------
OUT_STAB = ["XZZXI", "IXZZX", "XIXZZ", "ZXIXZ"]
OUT_X = "XXXXX"
OUT_Z = "ZZZZZ"

# --- [[4,2,2]] operators, 4 qubits, for conventions checks -------------------
S422 = ["XXXX", "ZZZZ"]
X1BAR, Z1BAR = "XXII", "ZIZI"
X2BAR, Z2BAR = "XIXI", "ZZII"

N = 5


def ps(s):
    return stim.PauliString(s)


def all_paulis(n=N):
    for combo in itertools.product("IXYZ", repeat=n):
        yield stim.PauliString("".join(combo))


def check_frame(stabs, xbar, zbar, label):
    """A frame is valid iff stabilizers mutually commute, logicals commute with
    them, and Xbar/Zbar anticommute with each other."""
    S = [ps(s) for s in stabs]
    X, Z = ps(xbar), ps(zbar)
    for i, a in enumerate(S):
        for b in S[i + 1:]:
            assert a.commutes(b), f"{label}: stabilizers do not commute"
        assert a.commutes(X) and a.commutes(Z), f"{label}: logical anticommutes with stabilizer"
    assert not X.commutes(Z), f"{label}: Xbar/Zbar commute"
    return True


def symplectic_completion(zs):
    """Given n independent, mutually commuting Paulis zs[0..n-1], return xs[0..n-1]
    with {xs[i], zs[i]} = 0, [xs[i], zs[j]] = 0 for i != j, and [xs[i], xs[j]] = 0.

    Brute force over all 4^n Paulis (n=5 -> 1024), then fix mutual anticommutation
    by multiplying in the zs, which preserves all the zs-relations."""
    n = len(zs)
    xs = []
    for i in range(n):
        cand = None
        for p in all_paulis(n):
            if p.commutes(zs[i]):
                continue
            if all(p.commutes(zs[j]) for j in range(n) if j != i):
                cand = p
                break
        assert cand is not None, f"no destabilizer partner for generator {i}"
        # fix anticommutation against already-chosen partners
        for j in range(i):
            if not cand.commutes(xs[j]):
                cand = cand * zs[j]
        cand.sign = +1
        xs.append(cand)
    for i in range(n):
        assert not xs[i].commutes(zs[i])
        for j in range(n):
            if i != j:
                assert xs[i].commutes(zs[j]) and xs[i].commutes(xs[j])
    return xs


def frame_tableau(stabs, xbar, zbar):
    """Tableau T with T(Z_0)=Zbar, T(X_0)=Xbar, T(Z_j)=stab_j, T(X_j)=destabilizer_j.

    Slot 0 is the logical qubit; slots 1..4 are the stabilizer slots."""
    zs = [ps(zbar)] + [ps(s) for s in stabs]
    xs_partner = symplectic_completion(zs)
    xs = [ps(xbar)] + xs_partner[1:]
    # xbar must satisfy the same relations as the brute-forced partner of Zbar
    assert not xs[0].commutes(zs[0])
    for j in range(1, len(zs)):
        assert xs[0].commutes(zs[j]), "Xbar anticommutes with a stabilizer"
        if not xs[0].commutes(xs[j]):
            xs[j] = xs[j] * zs[0]
            xs[j].sign = +1
    return stim.Tableau.from_conjugated_generators(xs=xs, zs=zs)
