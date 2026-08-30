"""Turn a document file into the plain text the extractor reads.

    py -3 intake.py spec.pdf            print the text
    py -3 intake.py spec.pdf --report   print what was cleaned up and why

**Why this file is not two lines of pdfplumber.** The report promises that every
finding links back to the sentence it came from. Naive PDF text extraction breaks
that promise in three specific ways, all of them observed on real documents during
Experiment A:

  1. **Running headers splice into sentences.** A sentence that crosses a page break
     comes back as "... the controller shall SPEC-7720 Rev B 3 only consider a bottle
     filled ...", so the sentence is in the document but not in the extraction, and
     the citation never resolves.
  2. **Words break at line ends.** "oper-\\nating" is two tokens unless the hyphen is
     healed, and "operating" is then absent from the text.
  3. **Every line is its own line.** A sentence wrapped over four lines cannot be
     matched against a quotation unless the wrap is undone, but real paragraph breaks
     and headings must survive, or the structure the extraction relies on is gone.

`pdfplumber` is used because it is layout aware and MIT licensed. **PyMuPDF is
deliberately not used: it is AGPL and would poison a commercial product.** It happens
to be installed on this machine. Do not import it.

Nothing here calls a language model.
"""
import io
import os
import re
import sys

SUPPORTED = (".pdf", ".txt", ".md", ".text")

# A line ending in one of these is the end of a sentence, so the next line starts a
# new one. Anything else that wraps is joined back up.
_ENDS = re.compile(r'[.!?:;]["\')\]]?\s*$')
# A heading, a clause number, a bullet. These keep their own line whatever else happens.
_STRUCTURE = re.compile(r'^\s*(?:\d+(?:\.\d+)*\.?\s|[-*•●]\s|[A-Z][A-Z0-9 ,./-]{4,}\s*$)')


class IntakeError(Exception):
    pass


def read(path):
    """Read `path` and return {text, kind, pages, notes}.

    `notes` says what was changed, so a surprising extraction can be explained
    rather than guessed at.
    """
    if not os.path.exists(path):
        raise IntakeError(f"There is no file at {path}.")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return read_pdf(path)
    if ext in SUPPORTED:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            return {"text": f.read(), "kind": "text", "pages": None, "notes": []}
    raise IntakeError(
        f"{ext or 'that file type'} cannot be read. Give a PDF, or plain text.")


def read_pdf(path, data=None):
    """Extract text from a PDF, undoing the three things that break traceability."""
    try:
        import pdfplumber
    except ImportError:
        raise IntakeError("Reading PDFs needs pdfplumber. Install it with "
                          "`pip install pdfplumber`.")

    if data is None and not os.path.exists(path):
        raise IntakeError(f"There is no file at {path}.")
    src = io.BytesIO(data) if data is not None else path
    notes = []
    pages = []
    try:
        with pdfplumber.open(src) as pdf:
            for page in pdf.pages:
                # Lines are built from word geometry rather than taken from
                # extract_text, which groups anything within its y tolerance into one
                # line. On a real EU deliverable that pulled the page footer onto the
                # last line of the contents page, and a footer welded to body text is
                # the splice this module exists to remove. x_tolerance stays generous
                # because too small a value splits words mid-token, the "linu x"
                # failure that made citations unresolvable in Experiment A.
                words = page.extract_words(x_tolerance=1.6, y_tolerance=1)
                pages.append(_rows(words, page.height))
    except IntakeError:
        raise
    except Exception as e:
        raise IntakeError(f"That PDF could not be read: {e}")

    if not any(any(l["text"].strip() for l in p) for p in pages):
        raise IntakeError(
            "No text could be read from that PDF. It is probably a scan, so it holds "
            "pictures of words rather than words. Send a text PDF, or paste the text.")

    dropped = _strip_running(pages)
    if dropped:
        notes.append("Removed %d running header or footer line%s that repeated across "
                     "pages: %s" % (len(dropped), "" if len(dropped) == 1 else "s",
                                    ", ".join('"%s"' % d for d in dropped[:4])))

    text, joins = _reflow(pages)
    if joins["hyphens"]:
        notes.append("Rejoined %d word%s broken across a line end."
                     % (joins["hyphens"], "" if joins["hyphens"] == 1 else "s"))
    if joins["wraps"]:
        notes.append("Rejoined %d sentence%s that wrapped over more than one line."
                     % (joins["wraps"], "" if joins["wraps"] == 1 else "s"))
    if joins["pagebreaks"]:
        notes.append("Rejoined %d sentence%s that continued onto the next page."
                     % (joins["pagebreaks"], "" if joins["pagebreaks"] == 1 else "s"))
    return {"text": text, "kind": "pdf", "pages": len(pages), "notes": notes}


def _rows(words, height, tol=2.2):
    """Group words into visual lines, keeping where each line sat on the page.

    `margin` marks a line in the top or bottom band, which is where running heads,
    page numbers and document references live. Those are never joined into a
    paragraph, because a footer welded onto a sentence is exactly the splice that
    makes a citation impossible to resolve.
    """
    lines = []
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        if lines and abs(w["top"] - lines[-1]["top"]) <= tol:
            lines[-1]["words"].append(w)
        else:
            lines.append({"top": w["top"], "words": [w]})
    out = []
    for ln in lines:
        text = " ".join(x["text"] for x in sorted(ln["words"], key=lambda w: w["x0"]))
        out.append({"top": ln["top"], "text": text,
                    "margin": ln["top"] < height * 0.075
                              or ln["top"] > height * 0.915})
    return out


def _key(line):
    """A running header is the same line with a different page number on it."""
    return re.sub(r"\d+", "#", line.strip()).lower()


_PAGE_NO = re.compile(r"^\s*(?:page\s*)?\d+\s*(?:[/of|-]{1,4}\s*\d+)?\s*$", re.I)


def _candidates(page, edge=2):
    """Lines that could be a running head: first or last few, or in the margin band.

    Position on the page is not enough on its own. A document with generous margins
    puts its running head inside the text block, and one with tight margins puts
    ordinary body text in the band, so both signals are needed.
    """
    live = [ln for ln in page if ln["text"].strip()]
    picked = {id(ln) for ln in live[:edge] + live[-edge:]}
    picked |= {id(ln) for ln in live if ln["margin"]}
    return [ln for ln in live if id(ln) in picked]


def _strip_running(pages):
    """Drop lines that repeat at the edge of most pages, and page numbers always.

    The threshold is low on purpose. Only edge lines are candidates, so the cost of
    being wrong is small, and real documents carry more than one footer format: the
    EU deliverable this was tested on had a bare number on its front matter and a
    long document reference everywhere else, and neither alone reached a majority.
    """
    dropped = []
    seen = {}
    for pi, p in enumerate(pages):
        for ln in _candidates(p):
            seen.setdefault(_key(ln["text"]), set()).add(pi)
    threshold = max(2, int(len(pages) * 0.25))
    running = {k for k, v in seen.items() if len(v) >= threshold}
    for p in pages:
        for ln in _candidates(p):
            if _key(ln["text"]) in running or _PAGE_NO.match(ln["text"]):
                if ln["text"].strip() not in dropped:
                    dropped.append(ln["text"].strip())
                ln["drop"] = True
    return dropped


def _gap(page):
    """The usual distance between two lines on this page."""
    tops = [l["top"] for l in page]
    gaps = sorted(b - a for a, b in zip(tops, tops[1:]) if b - a > 0.5)
    return gaps[len(gaps) // 2] if gaps else 0


def _reflow(pages):
    """Undo line wrapping without destroying paragraphs, headings or page order."""
    counts = {"hyphens": 0, "wraps": 0, "pagebreaks": 0}
    out, carry = [], ""
    pending_break = False

    def flush():
        nonlocal carry
        if carry:
            out.append(carry.strip())
            carry = ""

    for pi, page in enumerate(pages):
        usual = _gap(page)
        prev_top = None
        if pi and carry:
            pending_break = True     # whatever joins next crossed a page boundary
        for ln in page:
            if ln.get("drop"):
                continue
            line = ln["text"].strip()
            if not line:
                continue
            # A line much further from its predecessor than the page's usual spacing
            # starts something new, and so does anything sitting in the margin.
            # A bigger gap only ends a paragraph if a sentence ended too. Justified
            # text stretches its line spacing, so a mid-sentence gap is common and
            # breaking there puts a line end back into the middle of a sentence,
            # which is what this whole module is trying to remove.
            far = (prev_top is not None and usual and not carry
                   and (ln["top"] - prev_top) > usual * 1.4)
            prev_top = ln["top"]
            # A heading stands alone. The length test separates "2.2 Line
            # composition" from "2.2 The controller shall only consider a bottle
            # filled once ...", which starts the same way and must keep its
            # continuation lines, or the sentence can never be matched again.
            heading = bool(_STRUCTURE.match(line)) and len(line) <= 60
            if ln["margin"] or heading:
                flush()
                if heading and out and out[-1] != "":
                    out.append("")     # a heading gets air above it, as in the original
                out.append(line)
                pending_break = False
                continue
            if far:
                # A PDF has no blank lines, only bigger gaps, so the gap is put back
                # as one. The line itself then STARTS the new paragraph: emitting it
                # standalone here is what used to leave a sentence's first line
                # stranded on its own.
                flush()
                if out and out[-1] != "":
                    out.append("")
                pending_break = False
            if not carry:
                carry = line
            elif carry.endswith("-") and re.match(r"^[a-z]", line):
                carry = carry[:-1] + line               # heal a word broken at a line end
                counts["hyphens"] += 1
                if pending_break:
                    counts["pagebreaks"] += 1
                    pending_break = False
            else:
                carry += " " + line
                counts["wraps"] += 1
                if pending_break:
                    counts["pagebreaks"] += 1
                    pending_break = False
            if _ENDS.search(carry):
                flush()
                pending_break = False
        # Deliberately no flush per page. A page boundary is not a paragraph boundary,
        # and flushing at one cuts every sentence that continues onto the next page,
        # which is precisely the citation failure this module exists to prevent.
    flush()
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n", counts


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    try:
        got = read(argv[1])
    except IntakeError as e:
        print("!", e)
        return 2
    if "--report" in argv:
        print("kind   :", got["kind"])
        print("pages  :", got["pages"])
        print("words  :", len(got["text"].split()))
        for n in got["notes"]:
            print("  -", n)
        return 0
    sys.stdout.write(got["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
