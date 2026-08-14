"""Table 3 resource counts: the value lives in the cell after the label cell."""
import sys

sys.path.insert(0, r"C:\Users\corri\Downloads")
from dochelp import all_text, make_swap  # noqa: E402
from scripts.document import Document  # noqa: E402

doc = Document("unpacked_v4", author="Verification audit", initials="VA",
               track_revisions=True, rsid="EFF7AD35")
ed = doc["word/document.xml"]
swap = make_swap(doc, ed)


def value_cell(label):
    for tc in ed.dom.getElementsByTagName("w:tc"):
        if all_text(tc).strip() == label:
            row = tc.parentNode
            cells = [c for c in row.childNodes
                     if getattr(c, "tagName", "") == "w:tc"]
            i = cells.index(tc)
            return cells[i + 1]
    raise ValueError(f"label cell not found: {label}")


n = 0
for label, old, new, why in [
    ("Ancilla qubits (max simultaneous)", "3", "4",
     "Sec. 4 names ancillas a1 through a4, and Sec. 4.5 measures four stabilizers using "
     "one ancilla each, so four are live at once."),
    ("Total qubits (max simultaneous)", "9", "10",
     "5 data + 4 ancilla + 1 flag."),
]:
    cell = value_cell(label)
    run = next(r for r in cell.getElementsByTagName("w:r") if all_text(r).strip() == old)
    swap(node=run, old=old, new=new, comment=why)
    n += 1

doc.save(validate=False)
print(f"applied {n} table edits")
