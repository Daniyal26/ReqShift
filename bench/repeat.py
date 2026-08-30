"""How much does the same document change between two readings?

    py -3 bench/repeat.py runs/optcl.job.json runs/optcl2.job.json
    py -3 bench/repeat.py --run examples/bottling_line.txt      (reads it twice)

Two passes over an 83 page specification produced 18 participants and then 20,
3,456 configurations and then 384, and a defect count of 3 and then 1. That was
noticed by accident, because the document happened to be run twice. A report
whose contents move when you run it again cannot be sent to a customer, so the
first thing this needed was a number rather than an impression.

What it compares, and why each one separately: the instability has to be located
before it can be fixed. If the participants agree and the dependencies do not,
that is a different repair from the reverse.
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    """Compare participants by their words, not their punctuation or casing."""
    return " ".join(str(s or "").lower().replace("/", " ").replace("-", " ").split())


def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    return len(a & b) / float(len(a | b))


STOP = {"the", "a", "of", "for", "and", "to", "at", "in", "on", "kv", "unit", "system"}


def words(s):
    return {w.strip("()&,.") for w in norm(s).split()} - STOP


def same_thing(x, y, threshold=0.5):
    """Do two labels name the same participant?

    Exact string matching says no to "managed ethernet fibre switch (EFS)" against
    "managed ethernet fibre switch (station LAN)", and to "common inverter battery
    set" against "battery set common to the inverters". Both pairs are obviously
    one participant described twice, so comparing strings measures the wording and
    not the reading. Overlapping words measure the thing.
    """
    wx, wy = words(x), words(y)
    if not wx or not wy:
        return False
    return len(wx & wy) / float(min(len(wx), len(wy))) >= threshold


def pair_up(xs, ys):
    """Greedy best-match pairing. Returns (matched pairs, only in xs, only in ys)."""
    left, right = list(xs), list(ys)
    pairs = []
    for x in list(left):
        best, score = None, 0.0
        for y in right:
            wx, wy = words(x), words(y)
            if not wx or not wy:
                continue
            sc = len(wx & wy) / float(min(len(wx), len(wy)))
            if sc > score:
                best, score = y, sc
        if best is not None and score >= 0.5:
            pairs.append((x, best))
            left.remove(x)
            right.remove(best)
    return pairs, left, right


def participants(job):
    return [norm(a.get("label") or a["type"]) for a in job["spec"]["actors"]]


def bounds(job):
    return {norm(a.get("label") or a["type"]): (a["lo"], a["hi"])
            for a in job["spec"]["actors"]}


def dep_shape(job):
    """Dependencies as (depender, provider, multiplicity), by participant.

    Goal NAMES differ between readings for the same thing, so comparing them
    directly would report a difference that is only a difference of wording.
    """
    owner = {g["name"]: g["owner"] for g in job["spec"]["goals"]}
    label = {a["type"]: norm(a.get("label") or a["type"]) for a in job["spec"]["actors"]}
    out = []
    for d in job["spec"]["deps"]:
        a, b = label.get(owner.get(d["from"])), label.get(owner.get(d["to"]))
        if a and b:
            out.append((a, b, d.get("mult")))
    return out


def findings(job):
    return [(f["kind"], norm(f.get("actor") or "")) for f in job.get("findings", [])
            if f["kind"] != "inert-cardinality"]


def gaps_of(job):
    return [(norm(g["label"]), g.get("kind"), g["severity"]) for g in job.get("gaps") or []]


def pct(x):
    return "%.0f%%" % (100.0 * x)


def compare(a, b, name_a="run 1", name_b="run 2"):
    pa, pb = participants(a), participants(b)
    ba, bb = bounds(a), bounds(b)
    pairs, only_a_l, only_b_l = pair_up(pa, pb)
    match = {x: y for x, y in pairs}
    same_bounds = [x for x, y in pairs if ba.get(x) == bb.get(y)]
    shared = pairs

    da, db = dep_shape(a), dep_shape(b)
    fa, fb = findings(a), findings(b)
    ga, gb = gaps_of(a), gaps_of(b)
    sa, sb = a["result"]["stats"], b["result"]["stats"]

    print("%-26s %-22s %-22s" % ("", name_a, name_b))
    print("%-26s %-22s %-22s" % ("participants", len(pa), len(pb)))
    print("%-26s %-22s %-22s" % ("dependencies", len(da), len(db)))
    print("%-26s %-22s %-22s" % ("configurations", sa["configurations"], sb["configurations"]))
    print("%-26s %-22s %-22s" % ("outcome classes", sa["classes"], sb["classes"]))
    print("%-26s %-22s %-22s" % ("gaps", len(ga), len(gb)))
    print("%-26s %-22s %-22s" % ("findings (real problems)", len(fa), len(fb)))
    print()
    print("AGREEMENT, and where it breaks")
    total = len(pairs) + len(only_a_l) + len(only_b_l)
    print("  participants        %s  (%d matched, %d only in one reading)"
          % (pct(len(pairs) / float(total) if total else 1.0), len(pairs),
             len(only_a_l) + len(only_b_l)))
    print("  bounds on matched   %s  (%d of %d identical lo..hi)"
          % (pct(len(same_bounds) / float(len(pairs)) if pairs else 1.0),
             len(same_bounds), len(pairs)))
    # Dependencies are compared after translating run 2's names into run 1's, or
    # every pair would count as different for the same wording reason.
    db2 = [(match.get(x, x), match.get(y, y), m) for x, y, m in db]
    db2 = [(x, y, m) for x, y, m in db2]
    inv = {v: k for k, v in match.items()}
    db2 = [(inv.get(x, x), inv.get(y, y), m) for x, y, m in db]
    print("  dependency shape    %s" % pct(jaccard(da, db2)))
    # Gap labels ARE participant labels, so they were being paired a second time,
    # by `pair_up` over a list that contains duplicates because one participant can
    # carry several gaps. `pair_up` removes each match from the right-hand list, so
    # the second occurrence of a label matched whatever was left, which could be a
    # different participant entirely. The participants are already paired correctly
    # above, so reuse that and key the gaps by it.
    ka = {(x, k) for x, k, _ in ga}
    kb = {(inv.get(x, x), k) for x, k, _ in gb}
    print("  gaps (participant + kind)  %s  (%d vs %d distinct)"
          % (pct(jaccard(ka, kb)), len(ka), len(kb)))

    # One number hid two very different behaviours. Cardinality gaps come from the
    # bounds, which are audited. The others come from capacity, demand and duration
    # numbers, which are audited for PRECISION only: `verify_quantities` drops a
    # number the document does not support and nothing looks for one it missed. A
    # gap that exists only because a number happened to be extracted disappears
    # silently when it does not, which is the "no edge, no defect" failure one
    # layer over.
    print("  by kind:")
    for kinds, name in ((("cardinality",), "cardinality (the spine)"),
                        (("capacity", "demand", "timing"), "quantity derived")):
        A = {(x, k) for x, k, _ in ga if k in kinds}
        B = {(inv.get(x, x), k) for x, k, _ in gb if k in kinds}
        print("    %-24s %s  (%d vs %d)" % (name, pct(jaccard(A, B)), len(A), len(B)))

    # What the customer actually acts on. The report is ranked by severity and the
    # headline sentence names the critical count, so if that band moves, the
    # deliverable moves whatever the overall number says.
    for keep, name in (((("critical",)), "critical only"),
                       (("critical", "high"), "critical + high")):
        A = {(x, k) for x, k, s_ in ga if s_ in keep}
        B = {(inv.get(x, x), k) for x, k, s_ in gb if s_ in keep}
        print("  %-26s %s  (%d vs %d)" % (name, pct(jaccard(A, B)), len(A), len(B)))
    print("  findings            %s" % pct(jaccard(fa, fb)))

    only_a = sorted(only_a_l)
    only_b = sorted(only_b_l)
    if only_a or only_b:
        print("\n  participants only in %s:" % name_a)
        for x in only_a[:8]:
            print("     -", x[:70])
        print("  participants only in %s:" % name_b)
        for x in only_b[:8]:
            print("     -", x[:70])
    differing = [(x, ba[x], bb[y]) for x, y in pairs if ba.get(x) != bb.get(y)]
    if differing:
        print("\n  same participant, different bounds:")
        for k, x, y in differing[:8]:
            print("     %-46s %s..%s  vs  %s..%s" % (k[:46], x[0], x[1], y[0], y[1]))
    # These used to disagree with what was printed just above. `deps` compared the
    # untranslated names and `gaps` compared bare labels with no pairing at all, so
    # anything reading the return value got a harsher number than the report did,
    # for two different reasons. One measurement, one answer.
    def band(keep):
        A = {(x, k) for x, k, s_ in ga if s_ in keep}
        B = {(inv.get(x, x), k) for x, k, s_ in gb if s_ in keep}
        return jaccard(A, B)

    def kind(kinds):
        A = {(x, k) for x, k, _ in ga if k in kinds}
        B = {(inv.get(x, x), k) for x, k, _ in gb if k in kinds}
        return jaccard(A, B)

    return {
        "participants": len(pairs) / float(total) if total else 1.0,
        "bounds": len(same_bounds) / float(len(pairs)) if pairs else 1.0,
        "deps": jaccard(da, db2),
        "gaps": jaccard(ka, kb),
        "gaps_cardinality": kind(("cardinality",)),
        "gaps_quantity": kind(("capacity", "demand", "timing")),
        "gaps_critical": band(("critical",)),
        "gaps_critical_high": band(("critical", "high")),
        "findings": jaccard(fa, fb),
        # The headline sentence of the deliverable, so it is tracked as a number.
        "counts": {"gaps": (len(ga), len(gb)),
                   "critical": (sum(1 for _, _, s_ in ga if s_ == "critical"),
                                sum(1 for _, _, s_ in gb if s_ == "critical"))},
    }


def run_twice(path, port=8020):
    """Read one document twice through a running app.py and compare."""
    import urllib.request
    base = "http://127.0.0.1:%d" % port
    text = io.open(path, encoding="utf-8", errors="replace").read()
    jobs = []
    for i in (1, 2):
        req = urllib.request.Request(
            base + "/api/analyze",
            data=json.dumps({"text": text, "explain": False, "engine": "sat"}).encode(),
            headers={"Content-Type": "application/json"})
        jid = json.load(urllib.request.urlopen(req))["id"]
        t0 = time.time()
        while True:
            j = json.load(urllib.request.urlopen(base + "/api/job?id=" + jid))
            if j.get("state") != "running":
                break
            time.sleep(4)
        print("pass %d: %s in %.0fs" % (i, j.get("state"), time.time() - t0), flush=True)
        if j.get("state") != "done":
            raise SystemExit("pass %d did not finish: %s" % (i, str(j.get("errors"))[:200]))
        # Saved on purpose. The first time this ran, the two readings existed only
        # in the server's memory, so when one number looked wrong there was nothing
        # left to re-examine without spending another hour.
        out = os.path.join(ROOT, "runs", "%s.repeat%d.job.json"
                           % (os.path.basename(path).rsplit(".", 1)[0], i))
        io.open(out, "w", encoding="utf-8").write(json.dumps(j))
        print("        saved %s" % os.path.relpath(out, ROOT), flush=True)
        jobs.append(j)
    return jobs


def main(argv):
    if len(argv) >= 3 and argv[1] == "--run":
        a, b = run_twice(argv[2])
        compare(a, b, "first reading", "second reading")
        return 0
    if len(argv) >= 3:
        a, b = load(argv[1]), load(argv[2])
        compare(a, b, os.path.basename(argv[1]), os.path.basename(argv[2]))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
