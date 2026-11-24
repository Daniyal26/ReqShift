"""What corroboration cost, and what it changed.

Phase F. A second independent reading of the same document is used only to mark the
dependencies the first reading drew alone. Nothing is deleted, so the question is not
"how many edges survived" but "how many claims now say they rest on a doubted edge".

The prediction under test came from simulation: corroboration should cost about 14% of
edges. The help text quotes 31% from the singleton measurement. Both are guesses about
real material until this runs.
"""
import json
import os
import sys


def load(d):
    g = os.path.join(d, "gaps.json")
    return (json.load(open(os.path.join(d, "model.spec.json"), encoding="utf-8")),
            json.load(open(os.path.join(d, "analysis.json"), encoding="utf-8")),
            json.load(open(g, encoding="utf-8")) if os.path.exists(g) else [])


def main(run):
    spec, an, gaps = load(run)
    deps = spec.get("deps", [])
    ok = [d for d in deps if d.get("corroborated") is True]
    bad = [d for d in deps if d.get("corroborated") is False]
    unj = [d for d in deps if d.get("corroborated") is None]
    judged = len(ok) + len(bad)

    print("COST OF CORROBORATION")
    print("  dependencies              %d" % len(deps))
    print("  drawn by both readings    %d" % len(ok))
    print("  drawn by only one         %d" % len(bad))
    print("  not judgeable             %d  (a participant has no counterpart)" % len(unj))
    if judged:
        pct = 100.0 * len(bad) / judged
        print("  cost                      %.0f%% of judgeable edges" % pct)
        print("     simulation predicted 14%, the singleton measurement 31%")
    else:
        print("  cost                      not measurable, nothing was judgeable")

    findings = [f for f in an.get("findings", []) if f.get("kind") != "inert-cardinality"]
    print("\nFINDINGS  (%d)" % len(findings))
    for f in findings:
        marks = f.get("rests_on") or []
        tag = "PROVED" if f.get("proved", True) else "UNCONFIRMED"
        print("  [%s] %s" % (tag, f["headline"][:64]))
        for m in marks:
            print("        rests on %-22s %s" % (m.get("why"), str(m.get("what"))[:46]))
        if any(m.get("why") == "uncorroborated" for m in marks):
            print("        ^ THIS FINDING RESTS ON AN EDGE THE SECOND READING DID NOT DRAW")

    unc = [g for g in gaps if g.get("confirmed") is False]
    byunc = [g for g in gaps
             if any(m.get("why") == "uncorroborated" for m in (g.get("rests_on") or []))]
    print("\nGAPS  (%d, %d critical)"
          % (len(gaps), sum(1 for g in gaps if g.get("severity") == "critical")))
    print("  disclosed as unconfirmed        %d" % len(unc))
    print("  resting on an uncorroborated edge %d" % len(byunc))
    for g in byunc[:8]:
        print("     [%-8s] %s" % (g.get("severity"), str(g.get("actor"))[:52]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out_phaseF/corrob")
