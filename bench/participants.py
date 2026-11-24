"""Why two readings disagree about the participant list.

Phase E measured 60% participant agreement and Phase F found 20% of edges unjudgeable
for the same reason. Both were first read as "the matcher is the binding constraint".
Reading the actual pairs says otherwise, so this sorts every unmatched participant into
the reason it went unmatched and lets the split be re-measured instead of re-argued.

The labels are HEURISTIC. They exist to be eyeballed against the printed pairs, not to be
quoted as ground truth. Only ABSENT is certain, where nothing on the other side shares a
content word.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import corroborate as c

NUM = re.compile(r"^[0-9]+[a-z]?$")


def _split(label):
    """Content words and model numbers, kept apart.

    Model numbers are why `Gapping Unit (2335 / 2350)` scores 0.33 against the same
    device called `Gapping / Metering Device`. They are not noise in general though: two
    variants of one device are often distinguished by nothing else.
    """
    w = c._words(label)
    return {x for x in w if not NUM.match(x)}, {x for x in w if NUM.match(x)}


def _labels(spec):
    return [(a["type"], a.get("label") or a["type"]) for a in spec.get("actors", [])]


def classify(spec_a, spec_b):
    match = c.match_actors(spec_a, spec_b)
    taken = set(match.values())
    out = []
    for ta, label in _labels(spec_a):
        if ta in match:
            continue
        wa, _na = _split(label)
        # every candidate scored as the matcher would if model numbers were not in the
        # way, sorted so that a tie can be SEEN rather than silently resolved
        scored = sorted(((c._overlap(wa, _split(lb2)[0]), lb2, tb in taken)
                         for tb, lb2 in _labels(spec_b)), reverse=True)
        score, other, was_taken = scored[0] if scored else (0.0, None, False)
        runner = scored[1][0] if len(scored) > 1 else 0.0
        if score == 0.0:
            why = "ABSENT"
            note = "nothing on the other side shares a content word"
        elif score >= 0.5 and score - runner < 0.01:
            # `Gapping Unit` and `Belt of a High Rate Gapping Unit` both reach 1.00 once
            # the numbers go. Stripping numbers would not fix this, it would MIS-match it.
            why = "AMBIGUOUS"
            note = ("two candidates tie, so no rule on the label alone can pick, and "
                    "stripping model numbers would create a false match here")
        elif was_taken and score >= 0.5:
            why = "SPLIT/MERGE"
            note = "its best counterpart was already claimed, one side merged what the other split"
        elif score >= 0.5:
            why = "MATCHER"
            note = "reaches 0.5 on words alone, model numbers pushed it under the threshold"
        else:
            why = "WEAK"
            note = "partial overlap only, either a paraphrase or a real difference"
        out.append((why, label, other, score, note))
    return out


def main(fa, fb):
    a = json.load(open(fa, encoding="utf-8"))
    b = json.load(open(fb, encoding="utf-8"))
    rows = classify(a, b) + classify(b, a)
    print("participants %d and %d, matched %d, unmatched %d"
          % (len(a.get("actors", [])), len(b.get("actors", [])),
             len(c.match_actors(a, b)), len(rows)))
    for why in ("MATCHER", "AMBIGUOUS", "SPLIT/MERGE", "WEAK", "ABSENT"):
        got = [r for r in rows if r[0] == why]
        if not got:
            continue
        print()
        print("%s  (%d)" % (why, len(got)))
        print("   %s" % got[0][4])
        for _w, label, other, score, _n in got:
            print("     %-46s best %.2f  %s" % (label[:46], score, str(other)[:40]))

    fixable = sum(1 for r in rows if r[0] == "MATCHER")
    undecidable = sum(1 for r in rows if r[0] == "AMBIGUOUS")
    real = len(rows) - fixable - undecidable
    print()
    print("of %d unmatched:" % len(rows))
    print("  %d a better matcher would fix" % fixable)
    print("  %d undecidable from the labels alone. Both readings name the thing, but the"
          % undecidable)
    print("     same words fit a second candidate just as well")
    print("  %d the two readings genuinely disagree about what the document contains."
          % real)
    print("     That is not a matching problem and no matcher can repair it")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
