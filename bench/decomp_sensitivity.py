"""Is the behavioural classification sensitive to HOW a goal tree is carved up?

    py -3 bench/decomp_sensitivity.py runs/bottling.job.json runs/optcl2.job.json ...

Four independent readings of one specification agreed 100% on WHETHER a participant's
goal is broken down and only 12% on the exact shape of that breakdown, while returning
the same number of outcome classes. That suggested decomposition granularity is a
modelling choice the encoding does not react to, but it was four readings that differed
in several ways at once, so nothing was isolated.

This isolates it. Actors, bounds, dependencies, roots and operators are held FIXED and
only the shape of the tree is changed, in ways chosen so the logic is provably identical.

  deepen   an AND over [a, b, c] becomes an AND over [a, X] where X is a new AND over
           [b, c]. "All of a, b, c" and "a, and both of b and c" are the same claim.
  flatten  the reverse, inlining a child AND into its parent AND.

Both are semantics preserving, so a solver that reacts to them is reacting to notation.

The control is the operator scan. Relaxing an AND to an OR genuinely changes the claim,
so a run where nothing ever moves would mean the test measures nothing. Rather than flip
one node and hope, every AND is relaxed in turn and the ones that move are counted. That
number turned out to be the interesting result rather than the safety check.

An intermediate node is only introduced or removed when no dependency is attached to it
and it is not a root, because either would change what the model asserts.

Compared on the full multiset of satisfaction patterns, not on the class COUNT. Two runs
can produce the same number of classes and different classes.
"""
import copy
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import analyze  # noqa: E402


def load(path):
    with io.open(path, encoding="utf-8") as f:
        j = json.load(f)
    return j["spec"] if "spec" in j else j


def _attached(spec):
    """Goals that a dependency touches. Moving one of these changes the model."""
    out = set()
    for d in spec.get("deps", []):
        out.add(d.get("from"))
        out.add(d.get("to"))
    return out


def _roots(spec):
    return set((spec.get("roots") or {}).values())


def deepen(spec):
    """Split every AND of 3+ children into two nested ANDs. Semantics preserving."""
    s = copy.deepcopy(spec)
    owner = {g["name"]: g["owner"] for g in s["goals"]}
    n = 0
    for d in list(s.get("decomp", [])):
        kids = list(d.get("children") or [])
        if d.get("op") != "AND" or len(kids) < 3:
            continue
        n += 1
        new = "_deep%d" % n
        s["goals"].append({"name": new, "owner": owner[d["parent"]], "kind": "goal",
                           "root": False, "label": "grouped sub-goals %d" % n})
        s["decomp"].append({"parent": new, "op": "AND", "children": kids[1:]})
        d["children"] = [kids[0], new]
    return s, n


def flatten(spec):
    """Inline a child AND into its parent AND. Semantics preserving, the reverse move."""
    s = copy.deepcopy(spec)
    attached, roots = _attached(s), _roots(s)
    by_parent = {d["parent"]: d for d in s.get("decomp", [])}
    n = 0
    for d in list(s.get("decomp", [])):
        if d.get("op") != "AND":
            continue
        # This snapshot can contain a node that has since been inlined and deleted.
        # Working on it would delete its children's breakdowns while the real parent
        # still points at them, which is a dangling child, not a flatten.
        if not any(x is d for x in s.get("decomp", [])):
            continue
        for c in list(d.get("children") or []):
            child = by_parent.get(c)
            if not child or child.get("op") != "AND":
                continue
            if c in attached or c in roots:
                continue          # inlining it would change what the model asserts
            i = d["children"].index(c)
            d["children"] = d["children"][:i] + list(child["children"]) + d["children"][i + 1:]
            s["decomp"] = [x for x in s["decomp"] if x is not child]
            s["goals"] = [g for g in s["goals"] if g["name"] != c]
            by_parent.pop(c, None)
            n += 1
    return s, n


def flip(spec):
    """Turn a LOAD BEARING AND into an OR. The control: this should move.

    Picking the first AND is not good enough. On the substation models the first one
    had no dependency anywhere beneath it, so relaxing it changed nothing and the
    control silently failed. Which is itself the point of the whole experiment: most
    breakdowns in a real model are inert, and only the ones standing over a dependency
    decide anything. So the control looks for one of those.
    """
    s = copy.deepcopy(spec)
    attached = _attached(s)
    by_parent = {d["parent"]: d for d in s.get("decomp", [])}

    def carries(goal, seen=None):
        seen = seen or set()
        if goal in seen:
            return False
        seen.add(goal)
        if goal in attached:
            return True
        d = by_parent.get(goal)
        return bool(d) and any(carries(c, seen) for c in d.get("children") or [])

    for d in s.get("decomp", []):
        if d.get("op") != "AND" or len(d.get("children") or []) < 2:
            continue
        if sum(1 for c in d["children"] if carries(c)) >= 1:
            d["op"] = "OR"
            return s, 1
    return s, 0


def scan_operators(spec, base, goalshift_dir=None):
    """Relax every AND in turn and count how many actually change the behaviour.

    A single control flip kept coming back IDENTICAL on the substation models, which
    looked like a broken control and is not. Relaxing AND to OR can only make a goal
    EASIER to satisfy, so it changes nothing unless that AND was false somewhere. Most
    are never false. Rather than hunt for one that moves, measure how many do. That
    number IS the result: it says what share of a real goal tree carries any weight.
    """
    moved, tried = 0, 0
    for i, d in enumerate(spec.get("decomp", [])):
        if d.get("op") != "AND" or len(d.get("children") or []) < 2:
            continue
        s2 = copy.deepcopy(spec)
        s2["decomp"][i]["op"] = "OR"
        sig, _err = signature(s2, goalshift_dir)
        if sig is None:
            continue
        tried += 1
        if sig["patterns"] != base["patterns"] or sig["order"] != base["order"]:
            moved += 1
    return moved, tried


def signature(spec, goalshift_dir=None):
    """The behaviour, as the multiset of satisfaction patterns over the actor order."""
    r = analyze.analyze(spec, goalshift_dir)
    if not r.get("ok"):
        return None, r.get("errors", [])
    order = r["order"]
    pats = sorted(tuple(c["pattern"]) for c in r["classes"])
    return {"order": tuple(order), "patterns": tuple(pats),
            "classes": r["stats"]["classes"],
            "configurations": r["stats"]["configurations"]}, None


def run(path, goalshift_dir=None):
    spec = load(path)
    base, err = signature(spec, goalshift_dir)
    name = os.path.basename(path)
    if base is None:
        print("%-40s BASE DID NOT VALIDATE: %s" % (name[:40], str(err)[:60]))
        return None
    print("\n%s" % name)
    print("  base                        %d configurations, %d classes"
          % (base["configurations"], base["classes"]))
    rows = {}

    # The round trip. Most real trees are already flat, so `flatten` alone never
    # fires and the reverse direction goes untested. Deepening first manufactures
    # the nesting for it to remove, and returning to the original behaviour after
    # both edits is a stronger statement than either edit on its own.
    deep, nd = deepen(spec)
    if nd:
        back, nf = flatten(deep)
        sig, err = signature(back, goalshift_dir)
        if sig is None:
            print("  %-26s REJECTED: %s" % ("round trip deepen+flatten", str(err)[:40]))
        else:
            same = (sig["patterns"] == base["patterns"] and sig["order"] == base["order"])
            print("  %-26s %d in, %d out, %d classes -> %-9s  %s"
                  % ("round trip deepen+flatten", nd, nf, sig["classes"],
                     "IDENTICAL" if same else "CHANGED", "ok" if same else "UNEXPECTED"))
            rows["round trip deepen+flatten"] = same

    for label, fn, expect in (("deepen (adds a level)", deepen, "same"),
                              ("flatten (removes one)", flatten, "same")):
        s2, n = fn(spec)
        if not n:
            print("  %-26s not applicable" % label)
            continue
        sig, err = signature(s2, goalshift_dir)
        if sig is None:
            print("  %-26s REJECTED: %s" % (label, str(err)[:50]))
            rows[label] = None
            continue
        same = (sig["patterns"] == base["patterns"] and sig["order"] == base["order"])
        verdict = "IDENTICAL" if same else "CHANGED"
        ok = "ok" if ((expect == "same") == same) else "UNEXPECTED"
        print("  %-26s %d edit(s), %d classes  -> %-9s  %s"
              % (label, n, sig["classes"], verdict, ok))
        rows[label] = same

    moved, tried = scan_operators(spec, base, goalshift_dir)
    print("  %-26s %d of %d AND nodes change the behaviour when relaxed to OR"
          % ("operator sensitivity", moved, tried))
    rows["_moved"] = moved
    rows["_tried"] = tried
    return rows


def main(argv):
    paths = [a for a in argv[1:] if not a.startswith("--")]
    gs = None
    if "--goalshift" in argv:
        gs = argv[argv.index("--goalshift") + 1]
    if not paths:
        print(__doc__)
        return 1
    print("Holding actors, bounds, dependencies and roots FIXED. Changing only the "
          "shape of the goal trees.")
    tally, moved = {}, []
    for p in paths:
        r = run(p, gs)
        if not r:
            continue
        for k, v in r.items():
            if v is None or k.startswith("_"):
                continue
            tally.setdefault(k, []).append(v)
        moved.append((os.path.basename(p), r.get("_moved"), r.get("_tried")))
    print("\nACROSS %d SPECIFICATIONS" % len(paths))
    for k, v in tally.items():
        print("  %-26s identical behaviour in %d of %d" % (k, sum(v), len(v)))
    tot_m = sum(m for _n, m, t in moved if m is not None)
    tot_t = sum(t for _n, m, t in moved if t is not None)
    print("  %-26s %d of %d AND nodes carry any weight (%.0f%%)"
          % ("operator sensitivity", tot_m, tot_t,
             100.0 * tot_m / tot_t if tot_t else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
