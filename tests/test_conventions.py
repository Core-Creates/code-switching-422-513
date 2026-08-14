"""CONVENTIONS.md is the single source of truth. These tests fail if the conventions
are ever edited into an inconsistent state, which is the failure mode that produced
defect 1 in FINDINGS.md (Phase 2 measuring ZIZI instead of ZZII)."""
import frames as F
from frames import ps


def test_422_logical_assignment_is_consistent():
    for xb, zb, ox, oz, name in [
        (F.X1BAR, F.Z1BAR, F.X2BAR, F.Z2BAR, "logical 1"),
        (F.X2BAR, F.Z2BAR, F.X1BAR, F.Z1BAR, "logical 2"),
    ]:
        assert not ps(xb).commutes(ps(zb)), f"{name}: Xbar/Zbar must anticommute"
        assert ps(xb).commutes(ps(ox)) and ps(xb).commutes(ps(oz)), name
        for s in F.S422:
            assert ps(s).commutes(ps(xb)) and ps(s).commutes(ps(zb)), name


def test_sacrificed_logical_is_ZZII_not_ZIZI():
    """Defect 1: Sec. 4.3 measures ZIZI with controls on q1 and q3. ZIZI is Z1bar,
    the operator the protocol must preserve."""
    assert F.Z2BAR == "ZZII"
    assert F.Z1BAR == "ZIZI"
    assert F.Z2BAR != F.Z1BAR
    # measuring Z2bar must leave logical 1 untouched
    assert ps(F.Z2BAR).commutes(ps(F.X1BAR))
    assert ps(F.Z2BAR).commutes(ps(F.Z1BAR))
    # measuring Z1bar would destroy it
    assert not ps(F.Z1BAR).commutes(ps(F.X1BAR))


def test_both_five_qubit_frames_are_valid():
    assert F.check_frame(F.IN_STAB, F.IN_X, F.IN_Z, "input frame")
    assert F.check_frame(F.OUT_STAB, F.OUT_X, F.OUT_Z, "output frame")


def test_input_frame_matches_phase2_projection():
    """The input frame is the [[4,2,2]] code with Z2bar measured and a fresh q5."""
    assert F.IN_STAB == ["XXXXI", "ZZIII", "IIZZI", "IIIIZ"]
    assert F.IN_X == "XXIII" and F.IN_Z == "ZIZII"
    # ZZIII is Z2bar padded, IIZZI is Z2bar times the ZZZZ stabilizer
    assert ps("ZZIII") * ps("IIZZI") == ps("ZZZZI") or \
           str(ps("ZZIII") * ps("IIZZI")).lstrip("+-") == "ZZZZ_"
