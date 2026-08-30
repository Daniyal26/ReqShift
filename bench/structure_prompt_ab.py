"""Old dependency-audit prompt against the strict one, on the same model.

    py -3 bench/structure_prompt_ab.py runs/x.job.json path/to/document.txt

The prompt this compares against was not changed on a hunch. It judged
`BCPU_Measurement -> MFM_Root` as OK on the OPTCL specification, and the only
sentence behind that edge is

    "Additional Multifunction meter may be provided for monitoring the
     measurement, if monitoring of measurement is not available in BCPU."

which says the meter appears when the bay unit does NOT do the job, not that the
bay unit needs the meter. Read as a dependency it proved a defect the document
does not contain, and that defect was the one real finding on the first genuine
customer document.

So the strict prompt has to do two things at once and they pull against each
other. It has to reject an alternative, a connection and a list, and it must not
go back to rejecting the nine real dependencies that the one-sentence version
threw away and that emptied this same specification of its findings. Precision
without recall is the failure this tool already made once.

Both directions are printed per dependency, because a single agreement
percentage would hide which way each disagreement went.
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import verify


def verdicts(spec, trace, text, system_prompt, label):
    """Run the structure audit under one prompt and return {dep id: verdict}."""
    keep = verify.S_SYSTEM
    verify.S_SYSTEM = system_prompt
    try:
        t0 = time.time()
        out = verify.verify_structure(spec, trace, text)
        print("  %s: %d judged in %.0fs" % (label, out.get("checked", 0), time.time() - t0),
              flush=True)
    finally:
        verify.S_SYSTEM = keep
    return {r.get("id"): r for r in out.get("results", []) if isinstance(r, dict)}


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    job = json.load(io.open(argv[1], encoding="utf-8"))
    text = io.open(argv[2], encoding="utf-8", errors="replace").read()
    spec, trace = job["spec"], job.get("trace") or {}
    name = os.path.basename(argv[1])

    print("%s, %d dependencies" % (name, len(spec.get("deps", []))), flush=True)
    old = verdicts(spec, trace, text, verify.S_SYSTEM_BEFORE_STRICT, "old prompt")
    new = verdicts(spec, trace, text, verify.S_SYSTEM, "strict prompt")

    label = {a["type"]: (a.get("label") or a["type"]) for a in spec["actors"]}
    owner = {g["name"]: g["owner"] for g in spec["goals"]}
    src = (trace or {}).get("deps") or {}

    def v(d, table):
        return (table.get(d) or {}).get("verdict", "(no answer)")

    ids = [d["from"] + " -> " + d["to"] for d in spec.get("deps", [])]
    agree = [i for i in ids if v(i, old) == v(i, new)]
    stricter = [i for i in ids if v(i, old) == "ok" and v(i, new) == "unsupported"]
    looser = [i for i in ids if v(i, old) == "unsupported" and v(i, new) == "ok"]

    def count(table, verdict):
        return sum(1 for i in ids if v(i, table) == verdict)

    print("\n%-14s %-10s %-12s %s" % ("", "ok", "wrong_mult", "unsupported"))
    for nm, t in (("old prompt", old), ("strict", new)):
        print("%-14s %-10d %-12d %d"
              % (nm, count(t, "ok"), count(t, "wrong_mult"), count(t, "unsupported")))
    print("\nagreement %d of %d, newly rejected %d, newly accepted %d"
          % (len(agree), len(ids), len(stricter), len(looser)))

    for title, group in (("NEWLY REJECTED by the strict prompt", stricter),
                         ("NEWLY ACCEPTED by the strict prompt", looser)):
        if not group:
            continue
        print("\n" + title)
        for i in group:
            f, t = i.split(" -> ")
            print("  %s needs %s"
                  % (label.get(owner.get(f), "?")[:38], label.get(owner.get(t), "?")[:38]))
            print("    id    : %s" % i)
            print("    source: %s" % str(src.get(i, "(none)"))[:200])
            r = (new if i in stricter else old).get(i) or {}
            print("    why   : %s" % str(r.get("why") or "")[:200])

    # Both tables, not only the disagreements. The first run of this bench printed
    # differences alone, and the one dependency it was built to settle turned out to
    # be one the two prompts AGREED on, so the number that mattered was not in the
    # output and the run had to be paid for again.
    out = os.path.join(ROOT, "runs", name.rsplit(".job", 1)[0] + ".prompt_ab.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        {"old": old, "strict": new,
         "source": {i: src.get(i, "") for i in ids}}, indent=1))
    print("\nsaved %s" % os.path.relpath(out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
