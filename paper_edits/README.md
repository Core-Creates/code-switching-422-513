# paper_edits

Scripted tracked changes against `code_switching_paper.docx`. The manuscript revision is
reproducible like everything else in this repo: no edit is made by hand in Word.

## Run order

    python <docx-skill>/ooxml/scripts/unpack.py code_switching_paper.docx unpacked
    PYTHONIOENCODING=utf-8 PYTHONPATH=<docx-skill> python apply_all.py    # abstract, Sec. 3.3, Phases 1-2
    PYTHONIOENCODING=utf-8 PYTHONPATH=<docx-skill> python apply_rest.py   # Sec. 5, conclusion
    PYTHONIOENCODING=utf-8 PYTHONPATH=<docx-skill> python apply_table.py  # Table 3 counts
    python <docx-skill>/ooxml/scripts/pack.py unpacked code_switching_paper.docx

Point `UNPACKED` in each script at the same directory. The scripts are order-dependent
because each one re-reads the document after the previous one has split runs.

## What is produced

18 tracked deletions, 17 insertions, 16 explanatory comments. Every change carries a
comment naming the defect it fixes, keyed to the numbering in `../FINDINGS.md`.

## Verification

Schema validation is bypassed: the untouched original already fails the validator on
pre-existing `pgMar`, `w:tag` and `w:id` issues, so the check would only reproduce them.
Correctness is verified instead by a reject-all round trip. Strip every insertion,
restore every deletion, and the result must equal the original document text exactly.
It does. That is the check that proves no untracked edit slipped in.

## Gotcha worth remembering

`dochelp.text_of` exists because defusedxml's minidom splits a `<w:t>` into several text
nodes at character-entity boundaries. `firstChild.nodeValue` therefore silently truncates
any run containing a subscript or an arrow, which on the first attempt produced deletions
covering only part of the intended text. Always use the joined value.

The Section 3.3 gate listing is generated from `../encoder.stim` by
`dochelp.gate_listing`. Do not retype it.
