"""Does a sentence survive the trip through a PDF?

    py -3 bench/pdf_roundtrip.py

The report promises every finding links back to the sentence it came from, so the
only PDF test worth having is whether the sentences still match afterwards. This
takes a specification we already have as text, prints it to a PDF that is built to
break naive extraction, reads it back through `intake.py`, and checks that every
sentence and every eight word window of the original is still findable.

The PDF is hostile on purpose:
  * a running header and footer on every page, with the page number in them
  * a narrow page, so paragraphs wrap over many lines
  * a short page, so sentences are cut in half by page breaks

That is exactly the shape that produced unresolvable citations in Experiment A.

Chrome does the printing, since it is already used for the product PDFs. Point
CHROME at it if it is somewhere unusual.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import intake  # noqa: E402

CHROME = os.environ.get("CHROME") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DOCS = ["bottling_line.txt", "shuttle_warehouse.txt", "charging_site.txt"]

# A repeating header is done with thead/tfoot, which is how printed HTML actually
# repeats a running line on every page. CSS position:fixed was tried first and Chrome
# laid it on top of the body text, which is a broken PDF rather than a hostile one.
PAGE = """<!doctype html><meta charset="utf-8"><style>
@page {{ size: 108mm 132mm; margin: 12mm 12mm 11mm; }}
body {{ font: 10.5pt/1.5 Georgia, serif; margin: 0; }}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{ font: 7.5pt Arial, sans-serif; color: #555; font-weight: normal;
            text-align: left; border-bottom: .4pt solid #999;
            padding: 0 0 1.5mm; }}
tfoot td {{ font: 7.5pt Arial, sans-serif; color: #555; text-align: center;
            padding: 2mm 0 0; border-top: .4pt solid #ccc; }}
tbody td {{ padding: 3mm 0; }}
p {{ margin: 0 0 3mm; text-align: justify; }}
</style>
<table>
  <thead><tr><th>{head}</th></tr></thead>
  <tfoot><tr><td>Commercial in confidence</td></tr></tfoot>
  <tbody><tr><td>{body}</td></tr></tbody>
</table>
"""


def to_pdf(text, title, out):
    body = "".join("<p>%s</p>" % p.replace("\n", " ").strip()
                   for p in re.split(r"\n\s*\n", text) if p.strip())
    html = PAGE.format(head=title + " &nbsp;|&nbsp; Revision B &nbsp;|&nbsp; issued 2026",
                       body=body)
    src = out + ".html"
    io.open(src, "w", encoding="utf-8").write(html)
    profile = os.path.join(tempfile.gettempdir(), "reqshift_pdf_test_profile")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
           "--user-data-dir=" + profile, "--no-pdf-header-footer",
           "--print-to-pdf=" + out, "--virtual-time-budget=4000",
           "file:///" + src.replace("\\", "/")]
    subprocess.run(cmd, capture_output=True, timeout=120)
    os.remove(src)
    if not os.path.exists(out) or os.path.getsize(out) < 800:
        raise SystemExit("Chrome did not produce a PDF. Set CHROME to its path.")


def norm(s):
    return " ".join(re.sub(r"[\u2010-\u2015]", "-", s).split()).lower()


def sentences(text):
    flat = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", flat)
    return [p for p in parts if len(p.split()) >= 5]


def windows(text, n=8):
    w = norm(text).split()
    return [" ".join(w[i:i + n]) for i in range(0, max(0, len(w) - n + 1))]


def check(name):
    src_path = os.path.join(HERE, "examples", name)
    source = io.open(src_path, encoding="utf-8").read()
    pdf = os.path.join(tempfile.gettempdir(), name.replace(".txt", "") + ".test.pdf")
    to_pdf(source, name.replace(".txt", "").replace("_", " ").upper(), pdf)

    got = intake.read(pdf)
    hay = norm(got["text"])

    sents = sentences(source)
    lost = [s for s in sents if norm(s) not in hay]
    wins = windows(source)
    miss = [w for w in wins if w not in hay]

    ok = not lost and not miss
    print("%-26s %s  %d pages, %d words" % (
        name, "PASS" if ok else "FAIL", got["pages"] or 0, len(got["text"].split())))
    for n in got["notes"]:
        print("      -", n)
    print("      sentences %d/%d resolve, windows %d/%d resolve"
          % (len(sents) - len(lost), len(sents), len(wins) - len(miss), len(wins)))
    for s in lost[:4]:
        print("      LOST SENTENCE:", s[:110])
    for w in miss[:6]:
        print("      LOST WINDOW  :", w)
    os.remove(pdf)
    return ok


if __name__ == "__main__":
    if not os.path.exists(CHROME):
        raise SystemExit("Chrome not found at %s. Set CHROME." % CHROME)
    results = [check(d) for d in DOCS]
    print("\n%d of %d documents survive the round trip."
          % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)
