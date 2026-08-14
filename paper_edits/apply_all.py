"""All tracked-change batches, applied in one pass against a clean unpack."""
import sys

sys.path.insert(0, r"C:\Users\corri\Downloads")
from dochelp import make_swap, text_of, rpr_of, gate_listing, all_text, find_one  # noqa: E402
from scripts.document import Document  # noqa: E402

ENCODER = r"C:\Users\corri\Documents\GitHub\code-switching-422-513\encoder.stim"
UNPACKED = "unpacked_v4"

doc = Document(UNPACKED, author="Verification audit", initials="VA",
               track_revisions=True, rsid="EFF7AD31")
ed = doc["word/document.xml"]
swap = make_swap(doc, ed)
n_edits = 0


def edit(**kw):
    global n_edits
    n_edits += 1
    return swap(**kw)


# ============================================================ 1. Abstract
node = ed.get_node(tag="w:r", contains="approximately 15 CNOT gates. We analyze")
edit(node=node,
     old=("We prove that any single physical fault occurring during the switching "
          "procedure produces at most a weight-one error on the output code block, which "
          "lies within the correction capacity of the [[5,1,3]] code."),
     new=("We derive the re-encoding Clifford by frame composition rather than by hand, "
          "and verify it by two independent methods. We then prove a no-go result: of the "
          "fifteen weight-one errors present on the data block when re-encoding begins, "
          "twelve lie in a confusable pair and are therefore correctable by no encoder "
          "and no decoder, so the initial post-selection is load-bearing and the "
          "procedure is a state-preparation factory rather than an in-line switch. An "
          "exhaustive search over 97,466 valid flag placements, spanning all twenty-four "
          "stabilizer bijections and cascades of 15 to 25 two-qubit gates, finds no "
          "single-flag design that certifies the re-encoding phase; we report this as an "
          "open problem rather than a proof."),
     comment=("The weight-one claim is contradicted by Sec. 5.4.1, which itself produces "
              "weight-2 outputs at F2, F4, F5, F7 and F8, and it is unattainable in "
              "principle: see the new Lemma 1 in Sec. 5.1. Replaced with what the "
              "machine-checked artifacts actually establish."))

node = ed.get_node(tag="w:r", contains="approximately 15 CNOT gates. We analyze")
edit(node=node,
     old=("The complete circuit requires 5 data qubits, 3 ancilla qubits, 1 flag qubit, "
          "and approximately 15 CNOT gates."),
     new=("The verified re-encoder uses 17 two-qubit gates before optimization, and the "
          "complete protocol requires 5 data qubits, 4 ancilla qubits, 1 flag qubit, and "
          "79 two-qubit gates at three rounds of final syndrome extraction."),
     comment=("Exact counts read off the circuit files: Phase 0 = 8, Phase 1 = 1, "
              "Phase 2 = 2, Phase 3 = 17 for the verified re-encoder plus 3 for flag "
              "coupling, Phase 4 = 48 at r = 3. Total 79. Sec. 4 names ancillas a1 "
              "through a4 and Sec. 4.5 uses one ancilla per stabilizer, so the ancilla "
              "count is 4, not 3."))

# ============================================================ 2. Section 3.3
GATES = gate_listing(ENCODER)
ncx = sum(1 for g in GATES if g.startswith("CNOT"))
node = ed.get_node(tag="w:r", contains="U = (I ⊗ S₅)")
edit(node=node, old=text_of(node),
     new=("U = " + " · ".join(GATES) + ", applied left to right. This is "
          f"{ncx} CNOT gates and {len(GATES) - ncx} single-qubit gates, unoptimized; "
          "adjacent redundant pairs are retained so that the listing matches the "
          "verified circuit file exactly."),
     comment=("The original gate list does not perform the code switch. Conjugating the "
              "six frame generators through it gives XXXXI -> -ZXXIY, ZZIII -> ZZIIZ, "
              "IIZZI -> IIZZZ, IIIIZ -> YIIXX, XXIII -> XXIIZ, ZIZII -> ZIZIZ: zero of "
              "six correct, and the four stabilizer images are not even members of the "
              "[[5,1,3]] stabilizer group. The replacement is generated directly from "
              "encoder.stim, which is synthesized by frame composition and verified "
              "twice, by exact tableau conjugation including signs and by an independent "
              "float64 statevector check (leakage 1.8e-15, overlap 1.000000). Regenerate "
              "this listing from the file rather than editing it by hand."))

node = find_one(ed, "w:r", lambda t: t.startswith(" The gate decomposition above uses 6 CNOT"))
edit(node=node, old=text_of(node).lstrip(),
     new=("The verified re-encoder uses 17 CNOT gates, 12 Hadamards and 15 phase gates "
          "before optimization; these are integers read off the circuit file, not "
          "estimates. Flag-qubit coupling is discussed in Section 4.4, where an "
          "exhaustive search shows that no single bracketing-pair flag certifies this "
          "cascade."))

dup = find_one(ed, "w:p", lambda t: t.startswith("One can verify that the output states")
               and "gate decomposition above uses" in t)
if True:
    ed.suggest_deletion(dup)
    doc.add_comment(start=dup, end=dup,
                    text=("Duplicate of the preceding paragraph, carrying the same "
                          "incorrect gate counts. Deleted."))
    n_edits += 1

# ============================================================ 3. Phases 1, 2
edit(node=ed.get_node(tag="w:r", contains="Phase 2: measure"),
     old="Z̄₂ = ZIZI", new="Z̄₂ = ZZII",
     comment=("Sec. 3.1 defines Z2bar = ZZII and Z1bar = ZIZI. Measuring ZIZI destroys "
              "logical qubit 1, the qubit the protocol exists to preserve."))

edit(node=ed.get_node(tag="w:r", contains="To reduce from two logical qubits to one"),
     old=("Z̄₂ = ZIZI. This is performed indirectly: ancilla a₄ is prepared in |0⟩, CNOT "
          "gates with q₁ and q₃ as controls and a₄ as target realize the parity "
          "measurement (since Z̄₂ = ZIZI acts on qubits 1 and 3)"),
     new=("Z̄₂ = ZZII. This is performed indirectly: ancilla a₄ is prepared in |0⟩, CNOT "
          "gates with q₁ and q₂ as controls and a₄ as target realize the parity "
          "measurement (since Z̄₂ = ZZII acts on qubits 1 and 2)"),
     comment=("This is the most consequential error in the manuscript. As written, Phase "
              "2 measures ZIZI, which Sec. 3.1 defines as Z1bar, the logical operator "
              "carrying the information the switch must preserve. Controls belong on q1 "
              "and q2. Every downstream section inherits this error."))

edit(node=ed.get_node(tag="w:r", contains="A verification ancilla a₃ is prepared"),
     old=("A verification ancilla a₃ is prepared in |+⟩ (|0⟩ followed by Hadamard). A "
          "CNOT with q₅ as control and a₃ as target entangles them. A Hadamard is "
          "applied to a₃, which is then measured. If q₅ is correctly in |0⟩, the CNOT "
          "acts trivially on a₃, and the measurement yields 0 with certainty. If q₅ has "
          "suffered an X error and is in |1⟩, the CNOT flips a₃, and the subsequent "
          "Hadamard and measurement yield 1 with probability 1/2. By repeating this "
          "verification, the probability of an undetected preparation error is "
          "suppressed exponentially."),
     new=("A verification ancilla a₃ is prepared in |0⟩. A CNOT with q₅ as control and "
          "a₃ as target copies the computational-basis value of q₅ onto a₃, and a₃ is "
          "measured in the Z basis. If q₅ is correctly in |0⟩ the measurement yields 0; "
          "if q₅ has suffered an X error and is in |1⟩ the measurement yields 1 with "
          "certainty, so a single round detects the error deterministically rather than "
          "with probability 1/2."),
     comment=("As written the gadget detects nothing: a CNOT whose target is in |+> acts "
              "as the identity because X|+> = |+>, so a3 reads 0 regardless of q5. The "
              "correct gadget prepares a3 in |0> and measures Z. Note also that by Lemma "
              "1 (Sec. 5.1) errors on q5 are the only single-qubit input errors that are "
              "correctable at all, so this verification is a rate optimization, not a "
              "fault-tolerance requirement."))

doc.save(validate=False)
print(f"applied {n_edits} tracked edits")
