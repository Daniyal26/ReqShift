"""A second reading, used only to corroborate the dependencies of the first.

Measured across four independent readings of one 83 page specification, 31% of all
dependency edges were drawn by exactly one reading. Participants were fine at 5% and
the decomposition figure turned out to be a paraphrase artifact, so the edges are the
one place where the extraction genuinely invents at a rate worth paying to reduce.

An edge is identified by WHICH PARTICIPANTS it connects, never by goal names, because
two readings paraphrase a goal constantly and would agree on almost nothing if compared
by wording.

Nothing is deleted. An uncorroborated edge is MARKED, exactly as an unsupported one is,
because deleting edges was tried once and made a real specification come back with no
problems at all. Corroboration says how much weight a claim can carry, not whether it
survives.

Simulated over the six pairs available from four saved readings: requiring two readings
to agree costs 14% of the edges most readings agree on. That is the number that is a
real measurement. Removing edges only one reading drew is true by construction, since an
edge in one reading cannot appear in two.

This is the only part of ReqShift that reads the document twice, so it is opt in.
"""
import json

STOP = {"the", "a", "of", "for", "and", "to", "at", "in", "on", "kv", "unit", "system"}


def _words(s):
    s = str(s or "").lower().replace("/", " ").replace("-", " ")
    return {w.strip("()&,.") for w in s.split()} - STOP


def _overlap(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(min(len(a), len(b)))


def match_actors(spec_a, spec_b, threshold=0.5):
    """Map each participant in A to the one in B that names the same thing.

    Greedy best match on overlapping words. A participant is a proper noun and barely
    paraphrases, which is why this works here and would not work on goals: the same
    measurement that found 5% of participants unmatched found 41% of goal labels
    unmatched purely from rewording.
    """
    lab_a = [(a["type"], a.get("label") or a["type"]) for a in spec_a.get("actors", [])]
    lab_b = [(b["type"], b.get("label") or b["type"]) for b in spec_b.get("actors", [])]
    left = list(lab_b)
    out = {}
    for ta, la in lab_a:
        wa = _words(la)
        best, score = None, 0.0
        for tb, lb in left:
            sc = _overlap(wa, _words(lb))
            if sc > score:
                best, score = (tb, lb), sc
        if best and score >= threshold:
            out[ta] = best[0]
            left.remove(best)
    return out


def _pairs(spec, owner=None):
    """The set of participant pairs this model says depend on each other."""
    owner = owner or {g["name"]: g["owner"] for g in spec.get("goals", [])}
    out = set()
    for d in spec.get("deps", []):
        x, y = owner.get(d.get("from")), owner.get(d.get("to"))
        if x and y and x != y:
            out.add((x, y))
    return out


def mark_uncorroborated(spec_a, spec_b):
    """Mark every edge of A that the second reading did not also draw.

    Returns (spec, corroborated, uncorroborated, unmatched). `unmatched` counts edges
    whose participants have no counterpart in B at all: those cannot be judged either
    way and are left alone rather than being called uncorroborated, because absence of
    a participant is a different failure from absence of an edge.
    """
    match = match_actors(spec_a, spec_b)
    owner_a = {g["name"]: g["owner"] for g in spec_a.get("goals", [])}
    pairs_b = _pairs(spec_b)

    out = json.loads(json.dumps(spec_a))
    corroborated, uncorroborated, unmatched = [], [], []
    for d in out.get("deps", []):
        x, y = owner_a.get(d.get("from")), owner_a.get(d.get("to"))
        key = "%s -> %s" % (d.get("from"), d.get("to"))
        if not x or not y or x == y:
            continue
        mx, my = match.get(x), match.get(y)
        if mx is None or my is None:
            d["corroborated"] = None          # not judgeable, not a verdict
            unmatched.append(key)
            continue
        if (mx, my) in pairs_b:
            d["corroborated"] = True
            corroborated.append(key)
        else:
            d["corroborated"] = False
            uncorroborated.append(key)
    return out, corroborated, uncorroborated, unmatched


def second_reading(text, backend="auto", model=None):
    """Extract the document a second time, independently. One extra extraction call."""
    import extractor
    import schema
    extracted = extractor.extract(text, backend=backend, model=model)
    errors = schema.shape_errors(extracted)
    if errors:
        raise extractor.ExtractionError(
            "The second reading was malformed, so nothing was corroborated. "
            + "; ".join(errors[:3]))
    spec, _trace = schema.to_spec(extracted)
    return spec
