"""Did auditing the maximum steady the flag the gap report is built on?

    py -3 bench/bounds_agreement.py out_max1/model.spec.json out_max2/model.spec.json

The prediction being tested, written down before the runs finished so it cannot be
adjusted afterwards. Across readings of one specification the AUDITED field, `lo_stated`, agreed on every
participant while its UNAUDITED twin, `hi_stated`, did not. `gaps.build` raises a
cardinality gap exactly when `hi_stated` is false, so the gap count swung with it, 14
against 23 on the same unchanged document. All figures below are pairwise, which is why
running this on repeat1 against repeat2 reports a change of zero: that pair IS the
baseline.

`verify_maximums` should therefore move three numbers:

  hi_stated agreement   from 74%, toward the 100% that lo_stated reached
  hi agreement          from 79%
  gap count             should stop swinging (it was 14 against 23)

Participants are paired by word overlap, the same way `repeat.py` and `recall.py` pair
them, because two readings paraphrase a name and comparing strings would measure the
wording rather than the reading.

A pass that does not move `hi_stated` has not earned its API call and should come out.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from repeat import norm, pair_up  # noqa: E402

# The baseline measured THE SAME WAY as below, by pairing the two readings directly.
# The 12-of-17 figure quoted in PLAN.md came from clustering four readings and keeping
# consensus participants, which is a different denominator. Comparing a fresh pair
# against that would not be like for like, so the pairwise numbers from
# repeat1 vs repeat2 are used here.
BASELINE = {"lo": (19, 19), "hi": (15, 19),
            "lo_stated": (19, 19), "hi_stated": (14, 19)}


def load(path):
    with io.open(path, encoding="utf-8") as f:
        j = json.load(f)
    return j["spec"] if "spec" in j else j


def main(argv):
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if len(paths) < 2:
        print(__doc__)
        return 1
    a, b = load(paths[0]), load(paths[1])
    la = {norm(x.get("label") or x["type"]): x for x in a["actors"]}
    lb = {norm(x.get("label") or x["type"]): x for x in b["actors"]}
    pairs, only_a, only_b = pair_up(list(la), list(lb))

    print("participants: %d and %d, matched %d, only in one %d"
          % (len(la), len(lb), len(pairs), len(only_a) + len(only_b)))
    print()
    rows = []
    for field, get in (("lo", lambda x: x.get("lo")),
                       ("hi", lambda x: x.get("hi")),
                       ("lo_stated", lambda x: x.get("lo_stated")),
                       ("hi_stated", lambda x: x.get("hi_stated"))):
        # A field absent from BOTH readings is not agreement, it is a field nobody
        # recorded. Counting it as a match is how the first `lo_stated` measurement
        # produced a frightening 0% that turned out to be a version artifact.
        known = [(x, y) for x, y in pairs
                 if get(la[x]) is not None or get(lb[y]) is not None]
        same = sum(1 for x, y in known if get(la[x]) == get(lb[y]))
        base = BASELINE.get(field)
        tail = ""
        if base and base[1]:
            was = 100.0 * base[0] / base[1]
            now = 100.0 * same / len(known) if known else 0.0
            tail = "   was %.0f%% before the maximum audit, %+.0f points" % (was, now - was)
        print("  %-12s identical in %2d of %2d  (%.0f%%)%s"
              % (field, same, len(known), 100.0 * same / len(known) if known else 0, tail))
        rows.append((field, same, len(known)))

    print()
    for name, spec in ((os.path.basename(os.path.dirname(paths[0])), a),
                       (os.path.basename(os.path.dirname(paths[1])), b)):
        f = sum(1 for x in spec["actors"] if x.get("hi_stated") is False)
        print("  %-10s says the document states no maximum for %2d of %2d participants (%.0f%%)"
              % (name, f, len(spec["actors"]), 100.0 * f / len(spec["actors"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
