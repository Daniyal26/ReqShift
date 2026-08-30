"""The gap report. What the specification fails to specify.

Experiment A2, 23 Aug 2026: across ten real requirements documents, 72 of 76
extracted cardinality bounds were not supported by the text. 64 of those were
`no_number`, meaning the document never says how many of that thing exist.

Each one is a decision somebody has to make during design, currently
undocumented and currently invisible. Listing them is a smaller claim than
"your system is broken" and a far safer one, because it reports an ABSENCE,
which anyone can check by searching their own document.

Severity is derived from the model's own structure, never guessed:

    critical  the thing supplies something another actor needs through a
              1..* dependency, AND may be absent. The specification permits a
              system that boots with zero providers and cannot work.
    high      it supplies something another actor needs.
    medium    it needs things from others but supplies nothing.
    low       it stands alone, so its count changes no outcome.

A `wrong_unit` verdict outranks a `no_number` one at the same structural level,
because a wrong number may already have been used in a design decision, whereas
a missing one is at least visibly missing.
"""
import json
import re
import sys

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# How each doubted dependency reads in a sentence. Kept identical to report.WHY so
# the gap report and the findings report never describe the same flag two ways.
WHY = {"unsupported": "no sentence states it",
       "added": "an audit added it",
       "added-then-rejected": "one audit added it and another rejected it",
       "uncorroborated": "a second reading did not draw it"}


def _structure(spec):
    """Who supplies whom, read off the dependencies."""
    owner = {g["name"]: g["owner"] for g in spec["goals"]}
    supplies, needs, via_1star = {}, {}, {}
    for d in spec.get("deps", []):
        dg, pg = d.get("from"), d.get("to")
        depender, provider = owner.get(dg), owner.get(pg)
        if not depender or not provider or depender == provider:
            continue
        supplies.setdefault(provider, set()).add(depender)
        needs.setdefault(depender, set()).add(provider)
        if d.get("mult") == "1..*":
            via_1star.setdefault(provider, set()).add(depender)
    return supplies, needs, via_1star


def _edges(spec):
    """Dependency keys grouped by the participant at each end.

    `_structure` answers who supplies whom. This answers which EDGE said so, which is
    what a gap needs to name when the audits have doubted that edge.
    """
    owner = {g["name"]: g["owner"] for g in spec.get("goals", [])}
    by_provider, by_depender = {}, {}
    for d in spec.get("deps", []):
        dg, pg = d.get("from"), d.get("to")
        depender, provider = owner.get(dg), owner.get(pg)
        if not depender or not provider or depender == provider:
            continue
        key = "%s -> %s" % (dg, pg)
        by_provider.setdefault(provider, []).append((key, d.get("mult")))
        by_depender.setdefault(depender, []).append((key, d.get("mult")))
    return by_provider, by_depender


def attach_provenance(gap_list, spec, trace=None):
    """Carry each audit's flag from the dependency it sits on to the gap it produced.

    The findings learned this first. Gaps did not, and gaps are the deliverable. On a
    fresh document the single CRITICAL gap turned out to rest entirely on one
    dependency the structure audit had flagged `unsupported`, and the report said
    nothing about it.

    Two scopes, and the difference is not cosmetic:

      existence  a capacity or demand gap only exists because an edge connects the
                 two participants. Doubt the edge and the gap itself is doubtful.
      severity   a cardinality gap asks "how many of these are there", which the
                 document either answers or does not, whatever the edges say. The
                 gap is REAL either way. What rests on the edges is its RANKING,
                 because "critical" means "something needs this and there may be
                 none of it". Saying the gap is unconfirmed would be overreach.

    Mutates and returns `gap_list`.
    """
    import analyze
    trace = trace or {}
    quotes = (trace.get("deps") or {})
    deps = {"%s -> %s" % (d["from"], d["to"]): d for d in spec.get("deps", [])}
    by_provider, by_depender = _edges(spec)

    for g in gap_list:
        kind = g.get("kind", "cardinality")
        keys = list(g.get("rests_on_deps") or [])
        scope = "existence"
        if not keys and kind == "cardinality":
            scope = "severity"
            sev = g.get("severity")
            if sev == "critical":
                # "supplies X, and the specification allows there to be none at all",
                # which is true only of the 1..* edges into it.
                keys = [k for k, m in by_provider.get(g["actor"], []) if m == "1..*"]
            elif sev == "high":
                keys = [k for k, m in by_provider.get(g["actor"], [])]
            elif sev == "medium":
                keys = [k for k, m in by_depender.get(g["actor"], [])]

        rests, seen = [], set()
        for k in keys:
            m = analyze.dep_mark(deps.get(k), k, quotes.get(k, ""))
            if m and (m["why"], m["what"]) not in seen:
                seen.add((m["why"], m["what"]))
                rests.append(m)
        g["rests_on"] = rests
        g["rests_on_scope"] = scope if rests else None
        # Only meaningful where the whole gap hangs off the edges. A cardinality gap
        # stays confirmed, because nothing about a doubtful edge makes the document
        # start stating a number it never stated.
        g["confirmed"] = not (rests and scope == "existence")
    return gap_list


def _clean(s):
    """Tidy model prose for the report.

    Em dashes and en dashes are replaced with a comma, not deleted, because they
    are usually joining two clauses. The replacement character turns up when the
    PDF layer mangled a glyph and is simply dropped.
    """
    s = str(s or "").replace("—", ", ").replace("–", ", ")
    s = s.replace("�", " ").replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s*,\s*,", ",", s)
    return " ".join(s.split())


def build(spec, verify_results=None, trace=None):
    """Rank the quantities this specification never states.

    Two independent sources, either of which is enough:

      * `hi_stated: false` on an actor, set by the extraction itself. Free, no
        extra model call.
      * a failed verdict from `verify.py`, a separate second opinion.

    Using both means the report still works on models extracted before
    `hi_stated` existed, and a gap found by either route is reported once.
    """
    supplies, needs, via_1star = _structure(spec)
    by_type = {a["type"]: a for a in spec["actors"]}
    label = {a["type"]: a.get("label") or a["type"] for a in spec["actors"]}
    src = (trace or {}).get("actors", {})

    audited = {r.get("actor"): r for r in (verify_results or [])
               if isinstance(r, dict)}

    flagged = []
    for a in spec["actors"]:
        name = a["type"]
        r = audited.get(name)
        if r is not None:
            if r.get("verdict") != "ok":
                flagged.append((name, r))
            continue
        # No audit for this actor. Fall back to what the extraction itself said.
        if a.get("hi_stated") is False and a.get("hi", 1) > a.get("lo", 0):
            flagged.append((name, {"actor": name, "verdict": "no_number",
                                   "counts": "", "note": ""}))

    gaps = []
    for name, r in flagged:
        a = by_type.get(name)
        if not a:
            continue
        dependents_1star = via_1star.get(name, set())
        dependents = supplies.get(name, set())

        if dependents_1star and a.get("lo", 0) == 0:
            sev = "critical"
            why = (f"{label[name]} supplies "
                   f"{', '.join(sorted(label.get(d, d) for d in dependents_1star))}, "
                   f"and the specification allows there to be none at all.")
        elif dependents:
            sev = "high"
            why = (f"{label[name]} supplies "
                   f"{', '.join(sorted(label.get(d, d) for d in dependents))}, "
                   f"so how many exist decides whether that work can be done.")
        elif needs.get(name):
            sev = "medium"
            why = (f"{label[name]} depends on others but supplies nothing, so the count "
                   f"affects how much work is demanded, not whether it is possible.")
        else:
            sev = "low"
            why = f"{label[name]} is not linked to any other actor, so its count changes no outcome."

        gaps.append({
            "actor": name,
            "label": label[name],
            "severity": sev,
            "verdict": r.get("verdict"),
            "question": "The document never states how many of these can be present at once.",
            "to_decide": "Decide a minimum and a maximum, and write them into the specification.",
            "why_it_matters": _clean(why),
            "what_the_document_says": _clean(r.get("counts")),
            "note": _clean(r.get("note")),
            "claimed_bound_that_failed": a.get("hi"),
            "source_the_number_came_from": _clean(src.get(name, ""))[:300],
        })

    for g in gaps:
        g["kind"] = "cardinality"
    gaps += quantity_gaps(spec, trace)

    gaps.sort(key=lambda g: (SEVERITY_ORDER[g["severity"]],
                             0 if g["verdict"] == "wrong_unit" else 1,
                             g["label"]))
    return gaps


# ---------------------------------------------------------------------------
# The other half of a gap: capacity, demand and timing.
#
# A cardinality gap is reported whenever a count is missing, because a count is
# always needed. These are NOT reported that way, and the reason is the 72
# unranked gaps that made the first report unusable. "This document never states
# a capacity" is true of almost every document ever written, and saying so on
# every dependency is noise, not a finding.
#
# What IS a finding is an INCOMPLETE PAIR. The solver can only compute a capacity
# ceiling from `demand x depending instances <= capacity x providing instances`,
# so one side without the other is a number that can never be used. And the
# document itself raised the subject, which is what separates this from
# speculation: somebody wrote down how much each unit consumes and then never
# wrote down how much one provider can supply.
#
# The same shape applies to timing. A deadline with no durations under it cannot
# be checked against anything, and durations with no deadline have nothing to
# fail against.
# ---------------------------------------------------------------------------

def quantity_gaps(spec, trace=None):
    """Numbers whose other half is missing, so nothing can be computed from them."""
    src_a = (trace or {}).get("actors") or {}
    src_d = (trace or {}).get("deps") or {}
    label = {a["type"]: (a.get("label") or a["type"]) for a in spec.get("actors", [])}
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec.get("goals", [])}
    owner = {g["name"]: g["owner"] for g in spec.get("goals", [])}
    by_type = {a["type"]: a for a in spec.get("actors", [])}
    out = []

    def many(t):
        """More than one instance of this type can be present."""
        a = by_type.get(t) or {}
        return int(a.get("hi", 1)) > 1

    # ---- capacity and demand, ONE gap per provider -------------------------
    #
    # This used to loop over dependencies, so a provider with a stated capacity and
    # five dependers produced five demand gaps while the same provider with no
    # capacity produced none at all. The report's length therefore depended on
    # whether a capacity number happened to be extracted, and two readings of one
    # 83 page specification extracted 0 and 2 of them and produced 0 and 10 demand
    # gaps. That is the whole remaining swing in the gap count.
    #
    # Keyed on the dependency graph instead. Whether a provider serves several
    # dependers, or one that can be present many times, is a fact about the model
    # rather than about extraction luck, and the two readings agreed on that set
    # 88% of the time against essentially never for the numbers.
    #
    # One gap per provider, worded by what is known. Missing capacity asks for the
    # capacity. Known capacity with missing demand asks for the demand. Both known,
    # no gap. A provider whose capacity can never bind is left alone, because a
    # question that cannot change an answer is noise.
    serves, edges = {}, {}
    for d in spec.get("deps", []):
        depender = owner.get(d.get("from"))
        provider = owner.get(d.get("to"))
        if not depender or not provider or depender == provider:
            continue
        serves.setdefault(provider, set()).add(depender)
        edges.setdefault(provider, []).append(
            (f'{d["from"]} -> {d["to"]}', depender, d.get("demand")))

    for provider, dependers in serves.items():
        # Capacity binds when the provider is shared between kinds, or when the one
        # kind it serves can itself be present more than once.
        if len(dependers) < 2 and not any(many(t) for t in dependers):
            continue
        cap = (by_type.get(provider) or {}).get("capacity")
        who = ", ".join(sorted(label.get(t, t) for t in dependers))
        keys = [k for k, _t, _dem in edges.get(provider, [])]
        sev = "high" if any(many(t) for t in dependers) else "medium"

        if cap is None:
            out.append({
                "kind": "capacity", "actor": provider, "label": label[provider],
                "rests_on_deps": keys,
                "severity": sev,
                "verdict": "half_pair",
                "question": (f"The document never states how many units one "
                             f"{label[provider]} can serve at once."),
                "to_decide": (f"State the capacity of one {label[provider]}, and "
                              f"write it into the specification."),
                "why_it_matters": _clean(
                    f"{label[provider]} supplies {who}. Without a capacity, the real "
                    f"limit on how many of those the system can carry cannot be "
                    f"worked out, and the declared maximum may not be the real one."),
                "what_the_document_says": "",
                "note": "",
                "claimed_bound_that_failed": None,
                "source_the_number_came_from": _clean(src_a.get(provider, ""))[:300],
            })
            continue

        missing = sorted({label.get(t, t) for k, t, dem in edges.get(provider, [])
                          if dem is None})
        if missing:
            out.append({
                "kind": "demand", "actor": provider, "label": label[provider],
                "rests_on_deps": keys,
                "severity": sev,
                "verdict": "half_pair",
                "question": (f"The document says one {label[provider]} can serve "
                             f"{cap}, but never how much each of "
                             f"{', '.join(missing)} consumes."),
                "to_decide": (f"State what one of each takes from "
                              f"{label[provider]}, and write it into the "
                              f"specification."),
                "why_it_matters": _clean(
                    f"A capacity with nothing to spend it on cannot limit anything. "
                    f"Until the demand side is stated, the {cap} is a number in the "
                    f"document that no analysis can use."),
                "what_the_document_says": "",
                "note": "",
                "claimed_bound_that_failed": cap,
                "source_the_number_came_from": _clean(src_a.get(provider, ""))[:300],
            })

    # ---- timing ------------------------------------------------------------
    has_duration = {}
    for g in spec.get("goals", []):
        if g.get("duration") is not None:
            has_duration[owner.get(g["name"])] = True
    for a in spec.get("actors", []):
        t = a["type"]
        if a.get("deadline") is not None and not has_duration.get(t):
            out.append({
                "kind": "timing", "actor": t, "label": label[t],
                "severity": "high", "verdict": "half_pair",
                "question": (f"The document gives {label[t]} a deadline of "
                             f"{a['deadline']}, but never how long any of its steps "
                             f"take."),
                "to_decide": "State how long each step takes, in the same unit as the "
                             "deadline.",
                "why_it_matters": _clean(
                    f"A deadline can only be missed by something that takes time. With "
                    f"no step durations there is nothing to add up, so the deadline "
                    f"cannot be checked at all."),
                "what_the_document_says": "",
                "note": "",
                "claimed_bound_that_failed": a["deadline"],
                "source_the_number_came_from": _clean(src_a.get(t, ""))[:300],
            })
    # A duration with no deadline anywhere cannot change any outcome, which this
    # file already said and then raised a gap for anyway, once per participant that
    # happened to get a duration extracted. Two readings of one document extracted 2
    # durations and 14, producing 2 low gaps and 5, so the count measured extraction
    # luck rather than the document. It is still worth saying once, because a
    # specification full of step times and no deadline is a real omission. Once.
    no_deadline = sorted({label[t] for t in has_duration
                          if (by_type.get(t) or {}).get("deadline") is None})
    if no_deadline:
        out.append({
            "kind": "timing", "actor": None, "label": "Timing, across the system",
            "severity": "low", "verdict": "half_pair",
            "question": (f"Step durations are given for {len(no_deadline)} "
                         f"participant{'' if len(no_deadline) == 1 else 's'}, and the "
                         f"document sets no deadline for any of them."),
            "to_decide": "State the time by which the work has to finish, if there is one.",
            "why_it_matters": _clean(
                "Durations with no deadline have nothing to fail against, so they are "
                "recorded and never used. Nothing in this analysis changes until a "
                "deadline exists. The participants carrying durations are "
                + ", ".join(no_deadline) + "."),
            "what_the_document_says": "",
            "note": "",
            "claimed_bound_that_failed": None,
            "source_the_number_came_from": "",
        })
    return out


# ---------------------------------------------------------------------------
# Which gaps can actually change the answer.
#
# Severity above is STRUCTURAL: it reads the dependency graph and asks what a
# missing number is connected to. That is a proxy. The question a reader
# actually has is narrower and can be answered exactly, because there is a
# solver in the building:
#
#     if this number were 1, or 2, or 3, would anything about the result differ?
#
# The machinery is already here. `inert-cardinality` proves that a STATED range
# changes nothing across its span. The same test over a MISSING bound separates
# the gaps that can flip an outcome from the ones that cannot, with no model
# call at all.
#
# Two different things are tested, because they are different questions:
#
#   presence  does it matter whether any exist? (lo = 0 against lo = 1)
#   count     does the maximum matter?          (hi = 1 against 2 against 3)
#
# A gap that fails both cannot change the analysis whatever the reader answers,
# and saying so is what stops a long report from being a long list.
# ---------------------------------------------------------------------------

EFFECT_PROBE_HI = (1, 2, 3)
EFFECT_MAX_SPACE = 20000      # configurations, per probe. See MAX_INSTANCES in app.py.


def _classes_of(result, ignore=None):
    """The behaviour of a model, ignoring how the classes happen to be numbered.

    `ignore` drops one actor's own column from every pattern, and it is not
    optional for this test. An actor that is absent obviously reads differently
    in its OWN slot, so comparing whole patterns would report that every actor
    matters, which is the trivial answer to a different question. What is being
    asked here is whether this actor's count changes anything for the REST of
    the system.
    """
    if not result.get("ok"):
        return None
    order = result.get("order") or []
    idx = order.index(ignore) if ignore in order else None
    out = []
    for c in result.get("classes", []):
        pat = list(c["pattern"])
        if idx is not None and idx < len(pat):
            pat.pop(idx)
        out.append(tuple(pat))
    return sorted(set(out))


def _space(spec):
    n = 1
    for a in spec["actors"]:
        n *= max(0, int(a["hi"]) - int(a["lo"])) + 1
    return n


def _probe(spec, actor_type, lo, hi, analyzer):
    variant = json.loads(json.dumps(spec))
    for a in variant["actors"]:
        if a["type"] == actor_type:
            a["lo"], a["hi"] = lo, hi
            a.pop("hi_unknown", None)
    if _space(variant) > EFFECT_MAX_SPACE:
        return None
    try:
        return _classes_of(analyzer(variant), ignore=actor_type)
    except Exception:
        return None            # a probe that will not solve tells us nothing


def measure_effect(spec, actor_type, analyzer):
    """Can this actor's missing bound change the result? Returns a dict or None.

    None means the question could not be answered, usually because the model is
    too large to probe, and an unanswered question must never be reported as a
    "no".
    """
    a = next((x for x in spec["actors"] if x["type"] == actor_type), None)
    if a is None:
        return None

    counts = [_probe(spec, actor_type, min(1, int(a["lo"])), hi, analyzer)
              for hi in EFFECT_PROBE_HI]
    counts = [c for c in counts if c is not None]
    if len(counts) < 2:
        return None
    count_matters = len({tuple(c) for c in counts}) > 1

    absent = _probe(spec, actor_type, 0, max(1, int(a["hi"])), analyzer)
    present = _probe(spec, actor_type, 1, max(1, int(a["hi"])), analyzer)
    if absent is None or present is None:
        return {"count": count_matters, "presence": None}
    return {"count": count_matters, "presence": absent != present}


def rank_by_effect(spec, gap_list, analyzer):
    """Annotate every cardinality gap with what the analysis is sensitive to.

    Severity is not raised by this, only explained, and lowered in exactly one
    case: a gap that can change nothing at all. A gap whose PRESENCE matters
    stays critical even when its maximum is inert, because being able to build
    the system with none of them is the finding, not the ceiling.
    """
    for g in gap_list:
        if g.get("kind", "cardinality") != "cardinality":
            continue
        eff = measure_effect(spec, g["actor"], analyzer)
        if eff is None:
            g["effect"] = None
            continue
        g["effect"] = eff
        if eff["presence"] is True and eff["count"]:
            g["effect_says"] = ("Both halves of this matter. Whether any exist "
                                "changes the result, and so does how many.")
        elif eff["presence"] is True:
            g["effect_says"] = ("Whether any exist changes the result. The maximum "
                                "does not: 1, 2 or 3 give the same outcome, so the "
                                "minimum is the number that needs deciding.")
        elif eff["count"]:
            g["effect_says"] = ("How many exist changes the result, though the "
                                "system behaves the same whether or not any are "
                                "present at all.")
        elif eff["presence"] is False:
            g["effect_says"] = ("Tested against the solver, no value of this "
                                "changes the outcome. Worth writing into the "
                                "document, but it decides nothing here.")
            g["severity"] = "low"
            g["decides_nothing"] = True
    gap_list.sort(key=lambda g: (SEVERITY_ORDER[g["severity"]],
                                 0 if g["verdict"] == "wrong_unit" else 1,
                                 g["label"]))
    return gap_list


def to_markdown(gaps, doc_name="the specification", prescreen=None):
    """The deliverable. Findings first, severity first, no preamble."""
    out = [f"# What {doc_name} does not specify", ""]
    if not gaps:
        out += ["No unstated cardinalities were found. Every count this analysis needs "
                "is stated in the document.", ""]
        return "\n".join(out)

    counts = {}
    for g in gaps:
        counts[g["severity"]] = counts.get(g["severity"], 0) + 1
    summary = ", ".join(f"{counts[s]} {s}" for s in
                        ("critical", "high", "medium", "low") if s in counts)
    out += [f"**{len(gaps)} unstated {'quantity' if len(gaps) == 1 else 'quantities'}** "
            f"({summary}).", "",
            "Each one is a number the analysis needs, that the document does not give. "
            "Somebody decides each of these during design. Right now that decision is "
            "not written down.", ""]

    # What this list can and cannot promise, measured rather than assumed. Two
    # readings of the same 83 page specification agreed on 46% of the cardinality
    # gaps and on 8% of the rest. The difference is structural, not luck. A
    # cardinality gap is asked about EVERY participant, so it is raised whenever the
    # bound is missing. A capacity, demand or timing gap is only raised where a
    # RELATED number was extracted, because a demand with no capacity to check it
    # against cannot limit anything. When that related number is missed, no gap is
    # raised and the list is silently shorter. Saying so is the same rule the
    # findings follow. A gap that is listed is real. Absence is not evidence.
    kinds = {g.get("kind", "cardinality") for g in gaps}
    if kinds - {"cardinality"}:
        out += ["> **What this list promises.** Every participant was checked for a "
                "missing count, so the cardinality entries below are the complete "
                "set the analysis could find. The capacity, demand and timing "
                "entries are different. Each one is raised only where the document "
                "stated a related number, so this list reports the ones it found "
                "and cannot promise it found them all. Each entry is worth reading "
                "on its own. A short list is not a clean bill of health.", ""]

    if prescreen and not prescreen.get("in_scope"):
        out += ["> **Scope note.** This document was not written to describe a system "
                "whose composition varies, so some of the gaps below may be deliberate "
                "rather than accidental.", ""]

    for sev in ("critical", "high", "medium", "low"):
        block = [g for g in gaps if g["severity"] == sev]
        if not block:
            continue
        out += [f"## {sev.capitalize()}", ""]
        for g in block:
            out += [f"### {g['label']}", "",
                    f"**{g['question']}** {g['to_decide']}", "",
                    f"{g['why_it_matters']}", ""]
            if g.get("effect_says"):
                out += [f"*{g['effect_says']}*", ""]
            if g["verdict"] == "wrong_unit":
                out += [f"> A number *was* taken from the document for this, "
                        f"`{g['claimed_bound_that_failed']}`, but it counts "
                        f"{g['what_the_document_says'] or 'something else'}. "
                        f"Anyone reading quickly could make the same mistake.", ""]
            elif g["what_the_document_says"]:
                out += [f"> The document says: {g['what_the_document_says']}", ""]
            if g["note"]:
                out += [f"{g['note']}", ""]
            # The flag, on the claim it produced. A gap ranked critical because
            # something needs it is only as good as the edge that said so.
            for r in g.get("rests_on") or []:
                if g.get("rests_on_scope") == "existence":
                    lead = ("**This gap exists only because of a dependency the "
                            "audits doubted** (%s): `%s`" % (WHY[r["why"]], r["what"]))
                    tail = ("Without that dependency there is no pair to complete, so "
                            "this question may not need answering at all.")
                else:
                    lead = ("**Its ranking rests on a dependency the audits doubted** "
                            "(%s): `%s`" % (WHY[r["why"]], r["what"]))
                    tail = ("The missing number is still missing, and you can check "
                            "that by searching the document. What is in doubt is how "
                            "much it matters, because the severity comes from what "
                            "needs this participant.")
                out += [lead, "", r["note"], ""]
                if r.get("quote"):
                    out += ["> " + _clean(r["quote"]), ""]
                out += [tail, ""]
    out += ["---", "",
            "Every item above reports something the document does **not** contain. "
            "That is checkable: search the document and see.", ""]
    return "\n".join(out)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    spec = json.load(open(argv[1], encoding="utf-8"))
    audit = json.load(open(argv[2], encoding="utf-8"))
    trace = json.load(open(argv[3], encoding="utf-8")) if len(argv) > 3 else None
    gaps = build(spec, audit.get("results", audit), trace)
    print(to_markdown(gaps))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
