"""How much does ONE reading of a document miss?

    py -3 bench/recall.py runs/optcl.job.json runs/optcl2.job.json \
                          runs/optcl_substation_automation.repeat1.job.json \
                          runs/optcl_substation_automation.repeat2.job.json

    py -3 bench/recall.py <the same four> --against runs/optcl_repeat1_deprecall.json

`repeat.py` answers "do two readings agree", which is a symmetric question and cannot
say which reading was right. This answers the asymmetric one: **of everything the
document appears to describe, how much did a single pass find?**

There is no annotated ground truth for any of these documents and building one by hand
costs days. So the UNION of several independent readings stands in for it. That is not
ground truth and this file does not pretend it is. Two honest denominators are reported
instead:

  union      everything any reading proposed. Generous, because a single reading's
             invention lands in here too and counts against everybody else.
  consensus  everything a MAJORITY of readings proposed. Conservative, because an
             element only one reading saw is more likely an invention than a find.

**Recall against consensus is the number to watch.** Of the things most readings agree
are in the document, how many does one reading get?

The elements found by exactly one reading are reported separately, because that count
is the invention rate hiding inside the union.

IMPORTANT: pass only INDEPENDENT readings. `optcl_repeat1_deprecall.json` is repeat1
with the recall audit applied, not a separate reading of the document, so it belongs
after `--against` and never in the union.
"""
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from repeat import load, norm, words  # noqa: E402

THRESHOLD = 0.5


def overlap(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(min(len(a), len(b)))


def cluster(labelled):
    """Group labels that name the same thing across readings.

    `labelled` is [(run_index, label)]. Returns clusters, each a dict with the
    representative's words and the set of runs that proposed it.

    The representative's word set is FIXED at the first label seen. Growing it with
    every member would make each cluster easier to join than the last, and by the end
    a cluster would swallow anything. That is order dependent, which is why runs are
    processed in the order given and the count, not the naming, is what is reported.
    """
    out = []
    for run_i, label in labelled:
        w = words(label)
        if not w:
            continue
        best, score = None, 0.0
        for c in out:
            sc = overlap(w, c["words"])
            if sc > score:
                best, score = c, sc
        if best is not None and score >= THRESHOLD:
            best["runs"].add(run_i)
            best["labels"].add(label)
        else:
            out.append({"words": w, "rep": label, "runs": {run_i}, "labels": {label}})
    return out


def actor_clusters(jobs):
    """Cluster participants across readings, and map each run's type to its cluster."""
    labelled = []
    for i, j in enumerate(jobs):
        for a in j["spec"]["actors"]:
            labelled.append((i, norm(a.get("label") or a["type"])))
    cl = cluster(labelled)
    # run index -> actor type -> cluster id
    where = {}
    for i, j in enumerate(jobs):
        m = {}
        for a in j["spec"]["actors"]:
            lab = norm(a.get("label") or a["type"])
            for k, c in enumerate(cl):
                if lab in c["labels"]:
                    m[a["type"]] = k
                    break
        where[i] = m
    return cl, where


def dep_elements(jobs, where):
    """Dependencies keyed by the participant clusters they connect.

    Goal names differ between readings for the same thing, so an edge is identified by
    who needs whom, not by what the goals were called.
    """
    seen = {}
    for i, j in enumerate(jobs):
        owner = {g["name"]: g["owner"] for g in j["spec"]["goals"]}
        for d in j["spec"]["deps"]:
            a = where[i].get(owner.get(d["from"]))
            b = where[i].get(owner.get(d["to"]))
            if a is None or b is None or a == b:
                continue
            seen.setdefault((a, b), set()).add(i)
    return seen


def decomp_elements(jobs, where):
    """Breakdowns keyed by (participant cluster, cluster of the parent goal's label).

    Goal labels are clustered WITHIN each participant. Clustering them globally would
    merge "provide measurements" under one actor with the same phrase under another,
    and those are different breakdowns.
    """
    per_actor = {}
    for i, j in enumerate(jobs):
        owner = {g["name"]: g["owner"] for g in j["spec"]["goals"]}
        glabel = {g["name"]: norm(g.get("label") or g["name"]) for g in j["spec"]["goals"]}
        for d in j["spec"].get("decomp", []):
            ac = where[i].get(owner.get(d["parent"]))
            if ac is None:
                continue
            per_actor.setdefault(ac, []).append((i, glabel.get(d["parent"], d["parent"])))
    seen = {}
    for ac, labelled in per_actor.items():
        for k, c in enumerate(cluster(labelled)):
            seen[(ac, k)] = set(c["runs"])
    return seen


def report(name, elements, n_runs, run_names):
    """elements: {key: set(run indices that have it)}"""
    union = len(elements)
    need = int(math.floor(n_runs / 2.0)) + 1          # strict majority
    consensus = {k for k, v in elements.items() if len(v) >= need}
    singles = [k for k, v in elements.items() if len(v) == 1]

    print("\n%s" % name.upper())
    print("  union %d, consensus %d (in %d+ of %d readings), seen by only one reading %d"
          % (union, len(consensus), need, n_runs, len(singles)))
    print("  %-30s %-14s %-14s %s" % ("reading", "found", "recall vs union", "recall vs consensus"))
    rows = []
    for i in range(n_runs):
        mine = {k for k, v in elements.items() if i in v}
        r_u = len(mine) / float(union) if union else 1.0
        got = len(mine & consensus)
        r_c = got / float(len(consensus)) if consensus else 1.0
        only_me = sum(1 for k in singles if i in elements[k])
        print("  %-30s %-14d %-14s %s   (%d only this reading)"
              % (run_names[i][:30], len(mine), "%.0f%%" % (100 * r_u),
                 "%.0f%%" % (100 * r_c), only_me))
        rows.append({"run": run_names[i], "found": len(mine),
                     "recall_union": r_u, "recall_consensus": r_c,
                     "only_this_reading": only_me})
    avg = sum(r["recall_consensus"] for r in rows) / float(len(rows)) if rows else 1.0
    # The floor this number CANNOT go below, and the reason it must be quoted with it.
    # A consensus element is by definition held by at least `need` of the `n_runs`
    # readings, so averaged over readings it is already found at least need/n_runs of
    # the time before anything is measured. With 4 readings and a 3+ majority that
    # floor is 75%, so "93%" is a modest margin over the floor and not a good score.
    floor = need / float(n_runs)
    print("  average recall against consensus: %.0f%%   (structural floor %.0f%%, so the "
          "real margin is %+.0f points)"
          % (100 * avg, 100 * floor, 100 * (avg - floor)))
    # Uncircular by contrast. Nothing about the definition of consensus forces this.
    print("  proposed by exactly ONE of %d readings: %d of %d  (%.0f%%)"
          % (n_runs, len(singles), union, 100.0 * len(singles) / union if union else 0))
    return {"union": union, "consensus": len(consensus), "singletons": len(singles),
            "singleton_share": len(singles) / float(union) if union else 0.0,
            "avg_recall_consensus": avg, "floor": floor, "rows": rows}


def against(job, name, jobs, names, kind="deps"):
    """Score one EXTRA model against a consensus built from the independent readings.

    Used to ask whether a repair helped. `optcl_repeat1_deprecall` is repeat1 with the
    dependency recall audit applied, so it is not an independent reading and must not
    be in the union. Scoring it against that consensus is exactly the question: did the
    audit recover edges the other readings agree exist?

    Everything is re-clustered WITH the extra model present, because cluster ids are
    not comparable across two different clusterings. Consensus is still computed from
    the independent readings alone, so the extra cannot vote for itself. Every reading
    is printed in the same clustering rather than guessing which one the extra was
    derived from, since guessing that produced a recall that fell when edges were added,
    which is impossible and was the tell.
    """
    n = len(jobs)
    need = int(math.floor(n / 2.0)) + 1
    all_jobs = jobs + [job]
    _cl, where2 = actor_clusters(all_jobs)
    e2 = dep_elements(all_jobs, where2) if kind == "deps" \
        else decomp_elements(all_jobs, where2)
    independent = set(range(n))
    cons = {k for k, v in e2.items() if len(v & independent) >= need}
    print("\n  Re-clustered with %s present. Consensus (%d elements) still comes from "
          "the %d independent readings only." % (name, len(cons), n))
    for i, label in enumerate(names + [name + "  <- the repaired one"]):
        mine = {k for k, v in e2.items() if i in v}
        pc = 100 * (len(mine & cons) / float(len(cons)) if cons else 1.0)
        print("    %-42s %2d elements, recall %.0f%%" % (label[:42], len(mine), pc))


def main(argv):
    paths = [a for a in argv[1:] if not a.startswith("--")]
    extra = None
    if "--against" in argv:
        i = argv.index("--against")
        extra = argv[i + 1]
        paths = [p for p in paths if p != extra]
    if len(paths) < 2:
        print(__doc__)
        return 1

    jobs = [load(p) for p in paths]
    names = [os.path.basename(p) for p in paths]
    n = len(jobs)
    print("Union baseline from %d independent readings:" % n)
    for x in names:
        print("  -", x)

    cl, where = actor_clusters(jobs)
    actors = {k: set(c["runs"]) for k, c in enumerate(cl)}
    out = {}
    out["actors"] = report("participants", actors, n, names)
    deps = dep_elements(jobs, where)
    out["deps"] = report("dependencies", deps, n, names)
    dec = decomp_elements(jobs, where)
    out["decomp"] = report("decompositions", dec, n, names)
    print("  NOTE: this row is keyed by GOAL LABEL and its singleton share is not")
    print("  trustworthy. Goal names are free prose and paraphrase heavily, so one")
    print("  goal splits into several elements. Read the shape measure below instead.")
    out["shape"] = report_shapes(jobs, where, n, names)

    if extra:
        j = load(extra)
        print("\n" + "=" * 62)
        print("Does a repair recover what a single reading missed?")
        against(j, os.path.basename(extra), jobs, names, "deps")

    print("\nA reading that finds every element most readings agree on scores 100%.")
    print("Elements seen by only one reading are the invention rate inside the union.")
    return 0



# ---------------------------------------------------------------------------
# Decompositions, measured WITHOUT reading the goal names.
#
# The label-based measure above reported 41% of breakdowns as seen by only one
# reading, and reading those 20 by hand showed the number is mostly an artifact.
# A participant is a proper noun and paraphrases little, so clustering its name
# works. A GOAL is free prose and paraphrases enormously. The same GPS root goal
# came back as "synchronise the entire SAS to UTC", "provide co-ordinated
# universal time to the substation", "provide station wide time synchronisation"
# and "provide UTC traceable time synchronisation". Word overlap below the
# threshold splits one goal into four elements and calls two of them singletons.
#
# So measure the SHAPE instead, which is what actually decides satisfiability.
# Whether an actor's goal is a leaf or is broken down, into how many pieces, and
# with which operators, is the part the solver reacts to. What the pieces are
# called is not.
# ---------------------------------------------------------------------------

def tree_shape(job, where, run_i):
    """Per participant: (breakdown count, sorted operators, widest branching)."""
    owner = {g["name"]: g["owner"] for g in job["spec"]["goals"]}
    per = {}
    for d in job["spec"].get("decomp", []):
        ac = where[run_i].get(owner.get(d["parent"]))
        if ac is None:
            continue
        n, ops, wide = per.get(ac, (0, [], 0))
        per[ac] = (n + 1, ops + [d.get("op")], max(wide, len(d.get("children") or [])))
    return {ac: (n, tuple(sorted(o or "?" for o in ops)), w) for ac, (n, ops, w) in per.items()}


def report_shapes(jobs, where, n_runs, run_names):
    shapes = [tree_shape(j, where, i) for i, j in enumerate(jobs)]
    actors = set()
    for s in shapes:
        actors |= set(s)
    exact = decomposed = both_known = 0
    for ac in sorted(actors):
        vals = [s.get(ac) for s in shapes if ac in s]
        if len(vals) < 2:
            continue
        both_known += 1
        if len(set(vals)) == 1:
            exact += 1
        # The weaker question, and the one that changes an outcome: is this
        # participant's goal broken down at all, or is it a leaf that any
        # configuration satisfies?
        if len({v[0] > 0 for v in vals}) == 1:
            decomposed += 1
    print("\nDECOMPOSITION SHAPE (goal names not read)")
    print("  participants seen by 2+ readings: %d" % both_known)
    print("  identical shape (count, operators, branching): %d  (%.0f%%)"
          % (exact, 100.0 * exact / both_known if both_known else 0))
    print("  agree merely on broken down vs leaf:           %d  (%.0f%%)"
          % (decomposed, 100.0 * decomposed / both_known if both_known else 0))
    return {"compared": both_known, "identical": exact, "decomposed_agreement": decomposed}

if __name__ == "__main__":
    sys.exit(main(sys.argv))
