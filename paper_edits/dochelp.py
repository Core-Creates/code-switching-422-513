"""Shared helpers for the tracked-change batches.

The important one is text_of: defusedxml's minidom splits a <w:t> into several text
nodes at character-entity boundaries, so firstChild.nodeValue silently truncates any
run containing a subscript or an arrow. Every string comparison must use the joined
value or edits land on partial text.
"""
from xml.sax.saxutils import escape


def text_of(node):
    wt = node.getElementsByTagName("w:t")
    if not wt:
        return ""
    return "".join(c.nodeValue for c in wt[0].childNodes if c.nodeType == c.TEXT_NODE)


def rpr_of(node):
    return t[0].toxml() if (t := node.getElementsByTagName("w:rPr")) else ""


def make_swap(doc, ed):
    def swap(node, old, new, comment=None):
        """Minimal tracked edit: only the changed substring is marked."""
        rpr = rpr_of(node)
        full = text_of(node)
        if old not in full:
            raise ValueError(f"not found: {old[:60]!r} in {full[:120]!r}")
        i = full.index(old)
        pre, post = full[:i], full[i + len(old):]
        xml = ""
        if pre:
            xml += f'<w:r>{rpr}<w:t xml:space="preserve">{escape(pre)}</w:t></w:r>'
        xml += (f'<w:del><w:r>{rpr}<w:delText xml:space="preserve">{escape(old)}'
                f'</w:delText></w:r></w:del>')
        if new:
            xml += (f'<w:ins><w:r>{rpr}<w:t xml:space="preserve">{escape(new)}'
                    f'</w:t></w:r></w:ins>')
        if post:
            xml += f'<w:r>{rpr}<w:t xml:space="preserve">{escape(post)}</w:t></w:r>'
        nodes = ed.replace_node(node, xml)
        if comment:
            made = [n for n in nodes if getattr(n, "tagName", "") in ("w:del", "w:ins")]
            doc.add_comment(start=made[0], end=made[-1], text=comment)
        return nodes
    return swap


def gate_listing(path):
    """Generated from the circuit file. Never typed by hand."""
    import stim
    out = []
    for inst in stim.Circuit.from_file(path).flattened():
        tg = [t.value for t in inst.targets_copy()]
        if inst.name == "CX":
            out += [f"CNOT(q{a+1}→q{b+1})" for a, b in zip(tg[::2], tg[1::2])]
        else:
            out += [f"{inst.name}({'q%d' % (q + 1)})" for q in tg]
    return out


def all_text(node):
    """Join every <w:t> under a node (paragraph or run)."""
    out = []
    for wt in node.getElementsByTagName("w:t"):
        out.append("".join(c.nodeValue for c in wt.childNodes
                           if c.nodeType == c.TEXT_NODE))
    return "".join(out)


def find_one(ed, tag, pred):
    hits = [n for n in ed.dom.getElementsByTagName(tag) if pred(all_text(n))]
    if len(hits) != 1:
        raise ValueError(f"expected exactly 1 {tag}, got {len(hits)}")
    return hits[0]
