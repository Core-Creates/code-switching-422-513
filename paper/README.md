# paper

The manuscript is the LAST artifact, not the first.

    python paper/make_figures.py         # figures, from the circuits and result files
    python paper/generate_manuscript.py  # the document

`code_switching_paper_v2.docx` is generated. Do not edit it by hand: change the scripts,
or change the code the scripts read, and regenerate. Every number in the document is
pulled live from `encoder.stim`, `results/*.json`, or recomputed at generation time, so
the paper cannot drift from the repository.

## What changed from the first draft

The original argued that flag-protected re-encoding is fault tolerant. Section 5 of this
version proves it cannot be, so the old Sections 4.4 and 5.4, Algorithm 2, and Figures 2
and 4 are gone rather than corrected. The paper now carries three results: Lemma 1 on the
uncorrectability of residual input errors, the counting bound that closes the flag family,
and the certified teleportation switch with its numerics.

The previous document, with the tracked-change audit that led here, is preserved at
`Downloads/code_switching_paper.docx` with its untouched original alongside it. The
scripts that produced those redlines are in `../paper_edits/`.

## Figures

Both are generated. Figure 1 renders the joint measurement from the same stim circuit the
fault enumeration analyses. Figure 2 plots acceptance and logical error rate from
`results/numerics.json`, with the two fitted slopes in the title, since that comparison
is the cross-check between the combinatorial certificate and the Monte Carlo.
