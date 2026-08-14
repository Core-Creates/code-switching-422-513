"""Batches 4 and 5: the fault-tolerance sections and the conclusion.
Run AFTER apply_all.py, on the same unpacked directory."""
import sys

sys.path.insert(0, r"C:\Users\corri\Downloads")
from dochelp import make_swap  # noqa: E402
from scripts.document import Document  # noqa: E402

UNPACKED = "unpacked_v4"
doc = Document(UNPACKED, author="Verification audit", initials="VA",
               track_revisions=True, rsid="EFF7AD34")
ed = doc["word/document.xml"]
swap = make_swap(doc, ed)
n = 0


def edit(**kw):
    global n
    n += 1
    return swap(**kw)


edit(node=ed.get_node(tag="w:r", contains="We now prove that the switching protocol"),
     old=("is fault-tolerant for the [[5,1,3]] code: any single physical fault occurring "
          "during the protocol produces at most a weight-one error on the five output "
          "qubits."),
     new=("satisfies flag-conditioned correctability in the sense of Chamberland and "
          "Beverland [10]: for every single fault location, the pair (syndrome, flag) "
          "determines a correction that returns the block to the code space up to a "
          "stabilizer. This is the correct statement; the stronger claim that a single "
          "fault produces at most a weight-one output error is false, and Sections 5.1 "
          "and 5.4 below establish where it fails."),
     comment=("The weight-one formulation is contradicted by Sec. 5.4.1 itself, which "
              "produces weight-2 outputs at F2, F4, F5, F7 and F8, and it is unattainable "
              "by Lemma 1. Flag-conditioned correctability is what a flag gadget can "
              "deliver and what an enumeration certificate can prove."))

edit(node=ed.get_node(tag="w:r", contains="weight-preserving for weight-one errors"),
     old=("we rely on the subsequent phases: a weight-one error entering Phase 3 will "
          "produce at most a weight-one error on the output (since the re-encoding "
          "unitary is weight-preserving for weight-one errors by construction), which is "
          "correctable by the [[5,1,3]] code."),
     new=("no later phase can help. Lemma 1: partition the fifteen weight-one Paulis on "
          "the Phase 3 input block by their syndrome with respect to the frame "
          "(XXXXI, ZZIII, IIZZI, IIIIZ). The twelve supported on q₁ through q₄ fall into "
          "five classes, every one of which contains a pair whose product is a logical "
          "operator rather than a stabilizer; X₁ and X₂, for instance, share the syndrome "
          "(0,1,0,0) and differ by X̄₁ = XXII, which is exactly what distance 2 means. "
          "Since a Clifford is an isomorphism of the Pauli algebra, the images of such a "
          "pair are syndrome-identical and differ by a logical operator under every valid "
          "re-encoding unitary, so no encoder and no decoder can separate them. Only the "
          "three errors on the fresh ancilla q₅ are correctable, and a decoder "
          "synthesized for their images achieves all three. Consequently the "
          "post-selection in this phase is load-bearing: it is the only mechanism that "
          "removes these errors, and its fault tolerance belongs inside the theorem "
          "rather than in a remark. It also fixes the scope of the protocol as a "
          "state-preparation factory unless discard-and-restart is replaced by frame "
          "updates."),
     comment=("This parenthetical is the load-bearing false claim of the manuscript. A "
              "Clifford re-encoder is not weight-preserving, and no re-encoder can be "
              "made to work here: it is a property of the distance-2 input code, checked "
              "exhaustively against the Knill-Laflamme conditions for all 15 weight-one "
              "input errors."))

edit(node=ed.get_node(tag="w:r", contains="Fault F1 (X on q₅ after H gate"),
     old="Syndrome: (1,0,1,1).", new="Syndrome: (0,0,1,1).",
     comment="The syndrome of X on q5 with respect to (g1,g2,g3,g4) is (0,0,1,1).")

edit(node=ed.get_node(tag="w:r", contains="Fault F10 (Z on target q₅"),
     old=("Correction via syndrome lookup. Weight: 2 but identifiable. Correctable: Yes "
          "(Z₉Z₅ maps to a unique syndrome in the [[5,1,3]] code because each such pair "
          "is equivalent modulo stabilizers to a weight-1 error)."),
     new=("Correctable: No. Decoding Z₁Z₅, Z₂Z₅ and Z₃Z₅ with the standard weight-one "
          "table leaves residuals in the logical classes Y, X and X respectively. A "
          "weight-2 Z error is not in general stabilizer-equivalent to a weight-one "
          "error: in a perfect code the residual after a weight-one correction can have "
          "weight 3, and is then either a stabilizer or a logical operator. These three "
          "are logical."),
     comment=("Checked directly: Z1Z5 has syndrome (1,1,1,0) and decodes to logical Y; "
              "Z2Z5 has syndrome (0,0,0,1) and decodes to logical X; Z3Z5 has syndrome "
              "(0,1,1,0) and decodes to logical X. The subscript in the original is also "
              "mistyped as a numeral 9 rather than the index i."))

edit(node=ed.get_node(tag="w:r", contains="Flagged syndrome (1,0,0,1)"),
     old=("Flagged syndrome (1,0,0,1) → correction X₁X₅; Flagged syndrome (0,1,1,0) → "
          "correction X₂X₅; Flagged syndrome (1,1,0,0) → correction X₃X₅; Flagged "
          "syndrome (0,0,1,1) → correction X₄X₅;"),
     new=("Flagged syndrome (0,0,1,0) → correction X₁X₅; Flagged syndrome (1,0,1,1) → "
          "correction X₂X₅; Flagged syndrome (1,1,1,1) → correction X₃X₅; Flagged "
          "syndrome (0,1,0,1) → correction X₄X₅;"),
     comment=("All four syndromes were wrong; recomputed against (g1,g2,g3,g4). This "
              "table is in any case superseded: it was derived from the Sec. 3.3 gate "
              "list, which does not implement the code switch, and from the Sec. 4.4 "
              "gadget, which is not a flag. The decoder must be synthesized from an "
              "exhaustive fault enumeration over the verified cascade."))

edit(node=ed.get_node(tag="w:r", contains="every flagged syndrome listed in the switch"),
     old=("First, every flagged syndrome listed in the switch is distinct from the 15 "
          "weight-one syndromes of the standard [[5,1,3]] lookup, so the decoder is "
          "unambiguous on the listed patterns."),
     new=("First, because the [[5,1,3]] code is perfect its 15 nonzero syndromes are "
          "exhausted by the 15 weight-one errors, so every flagged syndrome necessarily "
          "coincides with the syndrome of some weight-one error. What makes the decoder "
          "unambiguous is conditioning on the flag bit, not distinctness of syndromes."),
     comment=("The original justification is not merely unproven, it is impossible, and "
              "it contradicts the perfectness described in Sec. 3.2. Flag conditioning is "
              "the correct argument."))

edit(node=ed.get_node(tag="w:r", contains="It uses a total of 9 qubits"),
     old=("It uses a total of 9 qubits (5 data, 3 ancilla, 1 flag) and approximately 15 "
          "CNOT gates. We have proven that the protocol satisfies the fault-tolerance "
          "condition for distance-3 codes: any single physical fault produces at most a "
          "weight-one error on the output, which is correctable by the [[5,1,3]] code. "
          "The flag qubit in the re-encoding phase is essential to this guarantee, "
          "preventing X-error cascades from producing uncorrectable multi-qubit errors."),
     new=("It uses a total of 10 qubits (5 data, 4 ancilla, 1 flag) and 79 two-qubit "
          "gates at three rounds of final syndrome extraction. We have established two "
          "results and left one problem open. First, the re-encoding Clifford is derived "
          "by frame composition and verified by two independent methods, at 17 two-qubit "
          "gates before optimization. Second, errors already present on the data block "
          "when re-encoding begins are correctable by no encoder and no decoder except on "
          "the fresh ancilla, which makes the initial post-selection load-bearing and "
          "scopes the protocol as a state-preparation factory. Open: an exhaustive search "
          "over 97,466 valid flag placements, across all twenty-four stabilizer "
          "bijections and cascades of 15 to 25 two-qubit gates, found no single "
          "bracketing-pair flag that certifies the re-encoding phase. Richer flag "
          "families, a measurement-based re-encoding, and the teleportation-based switch "
          "of Section 6.2 remain to be evaluated against the corrected resource counts."))

edit(node=ed.get_node(tag="w:r", contains="~15"), old="~15", new="79",
     comment=("Exact total across all five phases at r = 3, read off the circuit files. "
              "The re-encoder alone is 17."))

doc.save(validate=False)
print(f"applied {n} more tracked edits")
