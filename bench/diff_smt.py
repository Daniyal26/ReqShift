"""Differential test: the SMT backend against GoalShift's SAT engine.

GoalShift is the oracle. On every model both engines can express, the behavior
classes must come out the same. If they do not, the SMT encoding is wrong, and in
particular its one-Boolean-per-actor-type assumption is wrong.

    py -3 bench/diff_smt.py

Actor order can differ between engines only if the spec is reordered, which it is
not here, so classes are compared as a set of (pattern, member count) pairs. That
ignores class NUMBERING, which is compared separately, and ignores the concrete
member strings, which the two engines legitimately format differently once the
configuration space is too large to list.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import analyze as sat_side
import analyze_smt
from gen import make_spec


def classes_of(result):
    return sorted((tuple(c["pattern"]),
                   c.get("configurations", len(c["members"])))
                  for c in result["classes"])


def numbering_of(result):
    return sorted((tuple(c["pattern"]), c["class"]) for c in result["classes"])


def compare(name, spec):
    sat = sat_side.analyze(spec)
    smt = analyze_smt.analyze(spec)

    if not sat.get("ok") and not smt.get("ok"):
        print(f"  --  {name:34s} both reject it")
        return None
    if not sat.get("ok"):
        print(f"  ++  {name:34s} SAT rejects, SMT accepts: {sat['errors'][0][:60]}")
        return None
    if not smt.get("ok"):
        print(f"  !!  {name:34s} SMT rejects, SAT accepts: {smt['errors'][0][:60]}")
        return False

    same_classes = classes_of(sat) == classes_of(smt)
    same_numbers = numbering_of(sat) == numbering_of(smt)
    same_total = sat["stats"]["configurations"] == smt["stats"]["configurations"]

    if same_classes and same_numbers and same_total:
        print(f"  ok  {name:34s} {sat['stats']['configurations']:>7} configs, "
              f"{len(sat['classes'])} classes   "
              f"SAT {sat['stats']['sat_calls']:>6} calls / "
              f"SMT {smt['stats']['sat_calls']:>4} calls, "
              f"{smt['stats']['regions']} regions")
        return True

    print(f"  XX  {name}")
    if not same_total:
        print(f"        configurations  SAT {sat['stats']['configurations']}  "
              f"SMT {smt['stats']['configurations']}")
    if not same_classes:
        print(f"        SAT classes {classes_of(sat)}")
        print(f"        SMT classes {classes_of(smt)}")
    elif not same_numbers:
        print(f"        same classes, different numbering")
        print(f"        SAT {numbering_of(sat)}")
        print(f"        SMT {numbering_of(smt)}")
    return False


def main():
    if not analyze_smt.available():
        print("z3 is not installed.  pip install z3-solver")
        return 1

    cases = []
    for fn, label in (("casestudy_handbuilt.spec.json", "case study (hand-built)"),):
        p = os.path.join(ROOT, "examples", fn)
        if os.path.exists(p):
            cases.append((label, json.load(open(p, encoding="utf-8"))))
    for d in ("out", "out_ui", "out_domain", "out_full"):
        p = os.path.join(ROOT, d, "model.spec.json")
        if os.path.exists(p):
            cases.append((f"{d}/model.spec.json", json.load(open(p, encoding="utf-8"))))

    for nt in (2, 3, 4):
        for hi in (1, 2, 3):
            for depth in (1, 2):
                for mult in ("1..*", "*..*"):
                    for lo_first in (0, 1):
                        cases.append((
                            f"gen nt{nt} hi{hi} d{depth} {mult} lo{lo_first}",
                            make_spec(n_types=nt, hi=hi, depth=depth,
                                      dep_mult=mult, lo_first=lo_first)))

    print(f"Comparing the SMT backend against GoalShift on {len(cases)} models.\n")
    results = [compare(name, spec) for name, spec in cases]
    checked = [r for r in results if r is not None]
    bad = checked.count(False)
    print(f"\n{len(checked)} models compared, {bad} mismatch(es).")

    # The point of integers: a range the SAT engine cannot even attempt.
    print("\nRanges beyond what the SAT encoding can hold:")
    for hi in (10, 100, 10_000, 1_000_000):
        spec = make_spec(n_types=3, hi=hi, depth=2)
        smt = analyze_smt.analyze(spec)
        if smt.get("ok"):
            s = smt["stats"]
            print(f"  hi={hi:<9,} {s['configurations']:>21,} configurations, "
                  f"{s['regions']} regions, {s['classes']} classes, "
                  f"{s['sat_calls']} SMT calls")
        else:
            print(f"  hi={hi:<9,} rejected: {smt['errors'][0]}")

    # And a lower bound above 1, which the SAT engine refuses outright.
    print("\nA lower bound the SAT encoding rejects:")
    spec = make_spec(n_types=3, hi=6, depth=1)
    for a in spec["actors"]:
        if a["type"] != "T0":
            a["lo"] = 3
    sat = sat_side.analyze(spec)
    smt = analyze_smt.analyze(spec)
    print("  SAT: " + ("ok" if sat.get("ok") else sat["errors"][0]))
    if smt.get("ok"):
        print("  SMT: ok, %d classes over %d configurations"
              % (smt["stats"]["classes"], smt["stats"]["configurations"]))
    else:
        print("  SMT: " + smt["errors"][0])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
