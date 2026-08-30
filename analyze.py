"""Runs GoalShift and reads mechanical findings out of its result.

GoalShift is imported, never modified and never copied. If its engine changes, this
picks the change up; if this file has a bug, GoalShift is unaffected. That separation is
deliberate, because GoalShift is the artifact the thesis and the paper describe.

Nothing here uses a language model. Every finding below is derived arithmetically from
the solver's output, which is what makes them safe to put in front of an engineer.
"""
import os
import sys

DEFAULT_GOALSHIFT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "GoalModelTool")


def load_engine(goalshift_dir=None):
    """Import GoalShift's engine.py, read-only."""
    d = goalshift_dir or os.environ.get("GOALSHIFT_DIR") or DEFAULT_GOALSHIFT
    d = os.path.abspath(d)
    if not os.path.exists(os.path.join(d, "engine.py")):
        raise SystemExit(
            f"Could not find GoalShift's engine.py in {d}\n"
            f"Point at it with --goalshift <dir> or set GOALSHIFT_DIR.")
    if d not in sys.path:
        sys.path.insert(0, d)
    try:
        import engine
    except ModuleNotFoundError as e:
        if "pysat" in str(e):
            raise SystemExit("GoalShift's engine needs the SAT solver. "
                             "Install it with:  pip install python-sat")
        raise
    return engine


def analyze(spec, goalshift_dir=None):
    return load_engine(goalshift_dir).analyze(spec)


def _labels(spec):
    return {a["type"]: a.get("label") or a["type"] for a in spec["actors"]}


def findings(spec, result):
    """Everything worth flagging, derived only from the solver's output.

    Each finding is a dict with a kind, a one-line headline, the evidence behind it, and
    the actors involved, so the report and the optional write-up share one source.
    """
    if not result.get("ok"):
        return []

    order = result["order"]
    label = _labels(spec)
    goal_owner = {g["name"]: g["owner"] for g in spec["goals"]}
    goal_label = {g["name"]: (g.get("label") or g["name"]) for g in spec["goals"]}
    lo = {a["type"]: a["lo"] for a in spec["actors"]}
    out = []

    # Every other actor this actor's goals lean on, via a dependency.
    def providers(actor):
        seen = []
        for d in spec["deps"]:
            if goal_owner.get(d["from"]) != actor:
                continue
            provider = goal_owner.get(d["to"])
            if provider and provider != actor:
                seen.append((provider, d["from"], d["to"], d["mult"]))
        return seen

    # 1. Present but unsatisfied. The mode that costs money in the real world, because
    #    the equipment is switched on and provably cannot do its job. Reported once per
    #    actor, listing every class it happens in, rather than once per class.
    for i, actor in enumerate(order):
        hit = [c for c in result["classes"] if c["pattern"][i] == "X"]
        if not hit:
            continue
        causes, seen = [], set()
        for cls in hit:
            status = {order[k]: p for k, p in enumerate(cls["pattern"])}
            for provider, frm, to, mult in providers(actor):
                if status.get(provider) == "OK" or (provider, frm, to) in seen:
                    continue
                seen.add((provider, frm, to))
                causes.append({
                    "provider": label[provider],
                    # The raw names too, so `provenance` can find the dependency
                    # this cause is made of without matching on display labels.
                    "provider_type": provider, "dep": f"{frm} -> {to}",
                    "from_goal": frm, "to_goal": to, "depender": actor,
                    "from": goal_label.get(frm, frm), "to": goal_label.get(to, to),
                    "mult": mult,
                    # An absent provider and a present-but-broken one are different
                    # problems, and an engineer fixes them differently.
                    "why": "absent" if status.get(provider) == "-" else "present but unsatisfied",
                })
        out.append({
            "kind": "blocked",
            "actor": actor,
            "headline": f"{label[actor]} can be present and still unable to meet its goal",
            "classes": [c["class"] for c in hit],
            "configs": sum(len(c["members"]) for c in hit),
            "example": next((c["members"][0] for c in hit if c["members"]), ""),
            "absent": sorted({label[order[k]] for c in hit
                              for k, p in enumerate(c["pattern"]) if p == "-"}),
            "causes": causes,
        })

    # 2. An actor that is never satisfied in any configuration at all. Usually a
    #    modelling mistake or a genuinely unachievable requirement.
    for i, actor in enumerate(order):
        patterns = [c["pattern"][i] for c in result["classes"]]
        if "OK" not in patterns and "X" in patterns:
            out.append({
                "kind": "never-satisfied",
                "actor": actor,
                "headline": f"{label[actor]} is never satisfied in any configuration",
                "causes": [{"provider": label[c[0]], "provider_type": c[0],
                            "dep": f"{c[1]} -> {c[2]}",
                            "from_goal": c[1], "to_goal": c[2], "depender": actor,
                            "from": goal_label.get(c[1], c[1]),
                            "to": goal_label.get(c[2], c[2]), "mult": c[3],
                            "why": "absent" if lo.get(c[0]) == 0 else "unsatisfiable"}
                           for c in providers(actor)],
            })

    # 3. Does the system start out working? The initial configuration is every actor at
    #    its lower bound, which is the state the system boots into.
    init = tuple(a["lo"] for a in spec["actors"])
    for inst in result["instances"]:
        if tuple(inst["counts"]) == init and "X" in inst["pattern"]:
            unmet = [label[order[i]] for i, p in enumerate(inst["pattern"]) if p == "X"]
            # The same dependencies that block an actor are what leave it unsatisfied
            # at the minimum, and on a real specification one edge produced both
            # findings. Naming them here is what lets a flag on that edge reach this
            # finding too, instead of only the one that happened to list its causes.
            status = {order[k]: p for k, p in enumerate(inst["pattern"])}
            causes, seen = [], set()
            for k, p in enumerate(inst["pattern"]):
                if p != "X":
                    continue
                for provider, frm, to, mult in providers(order[k]):
                    if status.get(provider) == "OK" or (provider, frm, to) in seen:
                        continue
                    seen.add((provider, frm, to))
                    causes.append({
                        "provider": label[provider], "provider_type": provider,
                        "dep": f"{frm} -> {to}",
                        "from_goal": frm, "to_goal": to, "depender": order[k],
                        "from": goal_label.get(frm, frm), "to": goal_label.get(to, to),
                        "mult": mult,
                        "why": ("absent" if status.get(provider) == "-"
                                else "present but unsatisfied"),
                    })
            out.append({
                "kind": "initial-degraded",
                "headline": "The minimum configuration does not satisfy every present actor",
                "present": inst["present"],
                "pattern": inst["pattern"],
                "unmet": unmet,
                # The types as well as the labels. A doubtful root is a fact about
                # an actor, so it is reached by type, not by display name.
                "unmet_types": [order[i] for i, p in enumerate(inst["pattern"])
                                if p == "X"],
                "causes": causes,
            })
            break

    # 4. A cardinality range that changes nothing. Every extra instance is allowed by the
    #    requirements but makes no difference to any outcome, which is worth knowing
    #    before someone specifies capacity for it.
    for i, actor in enumerate(order):
        a = spec["actors"][i]
        if a["hi"] - a["lo"] < 2:
            continue
        by_count = {}
        for inst in result["instances"]:
            by_count.setdefault(inst["counts"][i], set()).add(inst["class"])
        nonzero = {k: v for k, v in by_count.items() if k > 0}
        if len(nonzero) > 1 and len({frozenset(v) for v in nonzero.values()}) == 1:
            out.append({
                "kind": "inert-cardinality",
                "actor": actor,
                "headline": (f"Nothing changes between 1 and {a['hi']} "
                             f"{label[actor]} instances"),
                "range": [a["lo"], a["hi"]],
            })
    return out


# ---------------------------------------------------------------------------
# Provenance: the other half of flag-not-remove.
#
# An audit that cannot tie a dependency to a sentence FLAGS it and leaves it in
# the model. That policy is right, and it was measured: removing unsupported
# edges made a real specification come back with no problems at all, and "no
# problems found" is the most dangerous output this tool produces.
#
# But the flag stopped at the edge. On the 83 page OPTCL specification the
# structure audit flagged `BCPU_Measurement -> MFM_Root` with the correct reason,
# that the multifunction meter is an optional substitute used when the BCPU lacks
# measurement monitoring rather than something the BCPU depends on. The flag went
# into a banner listing nine flagged edges. The one finding built on that same
# edge went into the headline as a proved defect. Both independent runs did this.
# The audit never missed it. The pipeline published the finding anyway.
#
# So the flag travels to the claim. The solver result does not change and is not
# in doubt: given the model, the finding is proved. What is in doubt is an input
# the document does not state. A finding resting on one is PROVED OF THE MODEL
# but UNCONFIRMED AGAINST THE DOCUMENT, and it now says so, in the same place it
# makes its claim, with the audit's own reason and the sentence beside it.
#
# Three inputs can be unconfirmed, and all three are things the model asserts
# that the document does not:
#   - a dependency the structure audit could not support,
#   - a dependency the extraction never drew and the recall audit added,
#   - an actor allowed to be absent only because the document never said, since
#     an absence is what makes "present and unable to do its job" possible.
# ---------------------------------------------------------------------------

UNCONFIRMED = {
    "unsupported":
        "No sentence in the document states this dependency. The structure audit "
        "flagged it and it was kept in the model on purpose, because removing "
        "unsupported edges hides real defects.",
    "added":
        "The extraction did not draw this dependency. The recall audit proposed it "
        "and a second pass confirmed it against the document.",
    # The loudest mark there is. Three passes looked at this edge and they did not
    # agree, and it is holding a finding up.
    "added-then-rejected":
        "The extraction never drew this dependency. The recall audit proposed it, a "
        "second pass confirmed it, and a third and stricter reading then rejected it "
        "and it was kept only so the disagreement is visible. Three passes disagree "
        "about whether the document states this at all, and a finding rests on it. "
        "Treat it as the least trustworthy thing in this report.",
    "uncorroborated":
        "A second, independent reading of the same document did not draw this "
        "dependency. Across four readings of one specification, 31% of all edges were "
        "drawn by exactly one reading, so an edge only one reading sees is the single "
        "most common way this tool invents something.",
    "assumed-absent":
        "The document does not say whether this can be absent. The analysis assumes "
        "it can, and that assumption is what makes this finding possible.",
    # The two inside an actor. A breakdown and a root are asserted claims exactly
    # like a dependency, and they are the ones the failure has to travel through
    # to become "this participant cannot meet its goal".
    "unsupported-breakdown":
        "No sentence in the document states that this goal is met by meeting the "
        "sub-goals under it. The failure reaches the participant's overall goal "
        "through this breakdown, so the claim is only as good as the breakdown is. "
        "It was kept in the model on purpose, because dropping a breakdown makes "
        "its goal trivially satisfied and would hide the defect rather than settle it.",
    "unsupported-root":
        "The document does not establish which goal is this participant's overall "
        "one. Every finding about it is phrased as failing to meet that goal, so "
        "what the finding is about is itself unsettled.",
    "wrong-root":
        "The audit reads a different goal as this participant's overall one. The "
        "finding says it cannot meet its goal, and which goal that is has been "
        "questioned, so the claim may be about the wrong thing entirely.",
}


def _tree(spec):
    """Child goal -> its parent, and parent goal -> the breakdown under it."""
    parent_of, by_parent = {}, {}
    for d in spec.get("decomp", []):
        by_parent[d["parent"]] = d
        for c in d.get("children", []):
            parent_of[c] = d["parent"]
    return parent_of, by_parent


def _ancestors(goal, root, parent_of):
    """The goals a failure at `goal` travels through on its way up to `root`.

    `goal` itself is excluded. The breakdown UNDER a goal is not what carries that
    goal's own failure upward, its parent's breakdown is. Guarded against a cycle
    and against a tree that never reaches the root, both of which a drafted model
    can contain.
    """
    out, seen, cur = [], {goal}, parent_of.get(goal)
    while cur and cur not in seen:
        seen.add(cur)
        out.append(cur)
        if cur == root:
            break
        cur = parent_of.get(cur)
    return out


def dep_mark(dep, key, quote):
    """What an audit said about one dependency, or None when it said nothing.

    Factored out so the gap report reads the same marks with the same wording. Two
    places describing the same flag in two different sentences is how a product
    starts contradicting itself.
    """
    if dep is None:
        return None
    flagged, added = dep.get("flagged") == "unsupported", bool(dep.get("added"))
    if flagged and added:
        # An edge an audit invented and another audit threw out. Reported as its own
        # thing, because "unsupported" alone loses the fact that it was never in the
        # document's own extraction either.
        note = UNCONFIRMED["added-then-rejected"]
        if dep.get("flag_why"):
            note += " The rejection reads: " + dep["flag_why"]
        return {"why": "added-then-rejected", "what": key, "note": note, "quote": quote}
    if flagged:
        return {"why": "unsupported", "what": key,
                "note": dep.get("flag_why") or UNCONFIRMED["unsupported"],
                "quote": quote}
    if added:
        return {"why": "added", "what": key, "note": UNCONFIRMED["added"], "quote": quote}
    # Checked last, because a flagged or audit-added edge already carries a stronger
    # statement and saying both would only dilute it.
    if dep.get("corroborated") is False:
        return {"why": "uncorroborated", "what": key,
                "note": UNCONFIRMED["uncorroborated"], "quote": quote}
    return None


def provenance(spec, trace, found):
    """Carry every unconfirmed input forward to the findings built on it.

    Mutates and returns `found`. Call it once, after any SMT extras have been
    added, so one pass covers both engines. Nothing here uses a language model.
    It only reads marks the audits already left on the model.
    """
    trace = trace or {}
    quotes = trace.get("deps") or {}
    actor_quotes = trace.get("actors") or {}
    decomp_quotes = trace.get("decomp") or {}
    goal_quotes = trace.get("goals") or {}
    deps = {f'{d["from"]} -> {d["to"]}': d for d in spec.get("deps", [])}
    label = _labels(spec)
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec.get("goals", [])}
    roots = spec.get("roots") or {}
    actors = {a["type"]: a for a in spec.get("actors", [])}
    parent_of, by_parent = _tree(spec)
    # Only an EXPLICIT False counts. The key is absent when the minimum audit never
    # ran, and "we did not check" must not be reported as "the document is silent".
    assumed = {a["type"] for a in spec.get("actors", [])
               if int(a.get("lo", 0)) == 0 and a.get("lo_stated") is False}

    def root_doubt(t):
        """The actor's overall goal, where the audit questioned which goal that is."""
        a = actors.get(t) or {}
        v = a.get("root_flagged")
        if not v:
            return None
        why = "wrong-root" if v == "wrong_root" else "unsupported-root"
        return {"why": why, "what": label.get(t, t),
                "note": a.get("root_flag_why") or UNCONFIRMED[why],
                "quote": goal_quotes.get(roots.get(t, ""), "") or actor_quotes.get(t, "")}

    def breakdown_doubts(cause):
        """Flagged breakdowns on the route from the failing goal up to the root.

        Scoped to that route on purpose. A doubtful breakdown in some other branch
        of the same actor has nothing to do with this failure, and marking every
        finding about the actor with it would make the mark mean nothing.
        """
        goal, t = cause.get("from_goal"), cause.get("depender")
        if not goal or not t:
            return []
        out = []
        for g in _ancestors(goal, roots.get(t), parent_of):
            d = by_parent.get(g)
            if not d or not d.get("flagged"):
                continue
            out.append({"why": "unsupported-breakdown", "what": glabel.get(g, g),
                        "note": d.get("flag_why") or UNCONFIRMED["unsupported-breakdown"],
                        "quote": decomp_quotes.get(g, "")})
        return out

    def unconfirmed(cause):
        """Every unstated input behind one cause. Empty when the document states it all."""
        out = []
        key = cause.get("dep") or ""
        m = dep_mark(deps.get(key), key, quotes.get(key, ""))
        if m:
            out.append(m)
        t = cause.get("provider_type")
        # Only where the absence is doing the work. A provider that is present and
        # itself unsatisfied does not rest on the minimum being zero.
        if cause.get("why") == "absent" and t in assumed:
            out.append({"why": "assumed-absent", "what": label.get(t, t),
                        "note": UNCONFIRMED["assumed-absent"],
                        "quote": actor_quotes.get(t, "")})
        out += breakdown_doubts(cause)
        return out

    for f in found:
        rests, seen = [], set()
        causes = list(f.get("causes") or [])
        # A capacity ceiling names its dependency directly rather than through a
        # cause, so it is checked the same way instead of escaping the pass.
        if f.get("dep"):
            causes.append({"dep": f["dep"]})
        for c in causes:
            marks = unconfirmed(c)
            c["provenance"] = [m["why"] for m in marks] or ["stated"]
            for m in marks:
                if (m["why"], m["what"]) in seen:
                    continue
                seen.add((m["why"], m["what"]))
                rests.append(m)
        # A doubtful root belongs to the finding rather than to any one cause. Every
        # kind here says an actor cannot meet ITS GOAL, and `inert-cardinality` is the
        # one that says nothing of the sort, so it is left out.
        if f["kind"] != "inert-cardinality":
            about = [f["actor"]] if f.get("actor") else list(f.get("unmet_types") or [])
            for t in about:
                m = root_doubt(t)
                if m and (m["why"], m["what"]) not in seen:
                    seen.add((m["why"], m["what"]))
                    rests.append(m)
        f["rests_on"] = rests
        # `inert-cardinality` claims nothing about the document, so it is neither.
        f["proved"] = not rests
    return found


def summary(spec, result, found):
    """One line per behavior class plus the headline counts, for the report header."""
    if not result.get("ok"):
        return {"ok": False, "errors": result.get("errors", [])}
    s = result["stats"]
    problems = [f for f in found if f["kind"] != "inert-cardinality"]
    unconfirmed = [f for f in problems if not f.get("proved", True)]
    return {
        "ok": True,
        "variables": s["variables"],
        "clauses": s["clauses"],
        "configurations": s["configurations"],
        "sat_calls": s.get("sat_calls"),
        "classes": s["classes"],
        "states": len(result["statechart"]["states"]),
        "transitions": len(result["statechart"]["edges"]),
        "problems": len(problems),
        # Split, because "3 problems found" and "3 problems found, 3 of them
        # resting on something the document does not state" sell very differently
        # and only one of them is true.
        "unconfirmed": len(unconfirmed),
        "proved": len(problems) - len(unconfirmed),
    }
