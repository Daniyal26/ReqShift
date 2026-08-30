"""Regenerate the "What comes back" panel on the landing page from a real run.

    py -3 bench/make_preview.py out_corrob

That panel shows a gap report with counts and quoted sentences, and its comment
claimed it was what the pipeline returns for that document. It was hand written, so
the claim was true when it was typed and had no way of staying true. The counts
still matched by luck; the wording had already drifted.

This writes the panel's data out of an actual run directory and splices it into
`ui/index.html` between two markers. Nothing is paraphrased, so the page cannot
say something the tool does not.

Re-run it whenever the gap logic changes. The check below fails loudly if the
markers are missing rather than writing the file into a broken state.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BEGIN = "  /* ---- BEGIN GENERATED PREVIEW"
END = "  /* ---- END GENERATED PREVIEW ---- */"


def build(run_dir, source_name=None):
    with io.open(os.path.join(run_dir, "gaps.json"), encoding="utf-8") as f:
        gaps = json.load(f)
    with io.open(os.path.join(run_dir, "model.spec.json"), encoding="utf-8") as f:
        spec = json.load(f)

    crit = sum(1 for g in gaps if g["severity"] == "critical")
    if crit == len(gaps) and len(gaps) == 2:
        unit = "both critical"
    elif crit == len(gaps) and crit:
        unit = "all critical"
    elif crit:
        unit = "%d critical" % crit
    else:
        unit = "none critical"

    def why(g):
        w = "<b>Why it matters.</b> " + g.get("why_it_matters", "")
        if g.get("effect_says"):
            w += " " + g["effect_says"]
        return w

    return {
        "file": source_name or os.path.basename(run_dir),
        "metrics": [
            {"label": "Unstated quantities", "value": len(gaps), "unit": unit,
             "tone": "bad" if gaps else "good"},
            {"label": "Participants found", "value": len(spec["actors"]),
             "unit": "and %d dependencies" % len(spec.get("deps", []))},
            {"label": "Solver", "value": "held", "unit": "until you supply them",
             "tone": "soft"},
        ],
        # Only the top few. The panel is a sample of the report, not the report.
        "gaps": [{"severity": g["severity"], "title": g["label"],
                  "what": g.get("question", ""), "why": why(g),
                  "source": g.get("source_the_number_came_from", "")}
                 for g in gaps[:3]],
    }


def splice(data, page=None):
    page = page or os.path.join(ROOT, "ui", "index.html")
    s = io.open(page, encoding="utf-8").read()
    i, j = s.find(BEGIN), s.find(END)
    if i < 0 or j < 0:
        raise SystemExit(
            "The generated-preview markers are not in %s. Refusing to write, because "
            "guessing where the block goes would corrupt the page." % page)
    block = (BEGIN + ", written by bench/make_preview.py.\n"
             "     Do not edit by hand: it is a real run's output, which is the only\n"
             "     reason the page can claim to show what the pipeline returns. ---- */\n"
             "  const PREVIEW = " + json.dumps(data, indent=2, ensure_ascii=False)
             .replace("\n", "\n  ") + ";\n")
    io.open(page, "w", encoding="utf-8", newline="\n").write(s[:i] + block + s[j:])
    return page


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    run = argv[1]
    name = argv[2] if len(argv) > 2 else None
    data = build(run, name)
    page = splice(data)
    print("preview rebuilt from %s" % run)
    print("  %s, %d gap(s) shown of the run's total" % (data["file"], len(data["gaps"])))
    for m in data["metrics"]:
        print("  %-22s %s  %s" % (m["label"], m["value"], m["unit"]))
    print("  spliced into %s" % os.path.relpath(page, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
