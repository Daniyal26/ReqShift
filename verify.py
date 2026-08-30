"""Second pass over the numbers. Checking is easier than extracting.

Experiment A, 22 Aug 2026, found that citations are honest and numbers are not.
The Clarus run set the number of environmental sensor stations to 4,700,000,
citing, perfectly correctly, "4.7 million road miles in North America". Road
miles are a distance, not a count of equipment. The library run turned "four
TYPES of printer" into four printers.

No citation check can catch either one, because the citation is right. What is
wrong is the reading of what the number counts.

So this asks a much narrower question than extraction, one bound at a time:

    does this sentence state how many of THIS THING exist?

That is nearly a yes/no question, which a model answers far more reliably than
"build me a goal model". It runs as a separate call with no memory of the
extraction, so it is not anchored to the first answer.

    py -3 verify.py out/model.spec.json out/model.trace.json requirements.txt
"""
import json
import sys

import extractor
from extractor import ExtractionError

SYSTEM = """You audit numbers that were pulled out of a requirements document by
another process. That process was often right about WHERE a number came from and
wrong about WHAT the number counts. Your only job is to catch the second kind of
mistake.

For each item you are given a kind of participant, a claimed maximum, and the
sentence the number was taken from.

Decide what the number in that sentence actually counts.

  - If it counts the participants themselves, the claim stands.
      "up to four welding robots"        -> counts welding robots. OK.
  - If it counts something else, the claim FAILS, however sensible it looks.
      "4.7 million road miles"           -> counts miles, not sensor stations.
      "four types of printer"            -> counts types, not printers.
      "20 million circulations per year" -> counts transactions, not branches.
  - If the sentence states no number at all for this participant, the claim FAILS
    and the correct answer is that the bound is unknown.

Be strict and be literal. A number that merely appears near the participant is not
a count of it. Where the claim fails, say what the number really counts. Do not try
to guess a better bound unless the sentence plainly gives one.

House style: never use em dashes or en dashes. Use a comma or a full stop instead."""

USER = """Audit these extracted bounds against the document.

<document>
{text}
</document>

<claims>
{claims}
</claims>

Answer with JSON only, no preamble. One entry per claim, same order:

{{"results": [{{"actor": "the name you were given",
                "counts": "what the number in the sentence actually counts",
                "verdict": "ok" or "wrong_unit" or "no_number",
                "correct_hi": a number if the sentence plainly gives one, else null,
                "note": "one short sentence, only when the verdict is not ok"}}]}}"""


def _ask(prompt, backend, model):
    """Send one audit prompt and return the parsed reply.

    Shared by both audits so they cannot drift apart on backend handling, which
    is the sort of difference that shows up only when one of them breaks.
    """
    if backend == "auto":
        options = extractor.available_backends()
        if not options:
            raise ExtractionError("No way to reach Claude for verification.")
        backend = options[0]
    if backend == "cli":
        exe = extractor._claude_cli()
        if not exe:
            raise ExtractionError("The `claude` command was not found on your PATH.")
        raw = extractor._run_cli(exe, prompt)
    else:
        import anthropic
        client = anthropic.Anthropic()
        r = client.messages.create(model=model or extractor.MODEL, max_tokens=8000,
                                   messages=[{"role": "user", "content": prompt}])
        raw = "".join(b.text for b in r.content if b.type == "text")
    return extractor._loads_loose(raw)


def verify(spec, trace, text, backend="auto", model=extractor.MODEL):
    """Audit every actor in `spec` that carries a cardinality range."""
    ranged = [a for a in spec["actors"] if a["hi"] > a["lo"]]
    if not ranged:
        return {"results": [], "checked": 0}

    lines = []
    for a in ranged:
        src = (trace.get("actors") or {}).get(a["type"], "(no source recorded)")
        lines.append(f'- actor: {a["type"]}\n  claimed maximum: {a["hi"]}\n'
                     f'  taken from: "{str(src)[:400]}"')
    prompt = SYSTEM + "\n\n" + USER.format(text=text, claims="\n".join(lines))

    out = _ask(prompt, backend, model)
    if not isinstance(out, dict) or "results" not in out:
        raise ExtractionError(f"Verification returned nothing usable.\n{raw[:400]}")
    out["checked"] = len(ranged)
    return out


def apply_verdicts(spec, results):
    """Return a copy of `spec` with failed bounds replaced by an honest unknown.

    A bound that failed the audit is worse than no bound, because the solver will
    treat it as fact. Rather than keep a wrong number, the actor is marked with
    `hi_unknown` and the bound is pulled back to something the document supports.
    """
    by = {r.get("actor"): r for r in results if isinstance(r, dict)}
    out = json.loads(json.dumps(spec))
    changed = []
    for a in out["actors"]:
        r = by.get(a["type"])
        if not r or r.get("verdict") == "ok":
            continue
        old = a["hi"]
        if isinstance(r.get("correct_hi"), int) and r["correct_hi"] >= a["lo"]:
            a["hi"] = r["correct_hi"]
        else:
            a["hi_unknown"] = True
            a["hi"] = max(a["lo"], 1)
        changed.append((a["type"], old, a["hi"], r.get("verdict"), r.get("counts")))
    return out, changed


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 1
    spec = json.load(open(argv[1], encoding="utf-8"))
    trace = json.load(open(argv[2], encoding="utf-8"))
    text = open(argv[3], encoding="utf-8", errors="replace").read()
    out = verify(spec, trace, text)
    bad = [r for r in out["results"] if r.get("verdict") != "ok"]
    print(f"checked {out['checked']} bounds, {len(bad)} failed")
    for r in bad:
        print(f"  ! {r.get('actor')}: {r.get('verdict')} "
              f"(the number counts {r.get('counts')!r})")
    return 0


# ---------------------------------------------------------------------------
# The other numbers.
#
# `verify()` above audits cardinalities, because those were what Experiment A
# proved unreliable. Capacity, demand, duration and a deadline are audited here
# for exactly the same reason, and the reason is sharper for them: an unchecked
# cardinality produces a wrong configuration COUNT, while an unchecked capacity
# produces a finding that reads "capped at 6", which sounds like a measurement.
#
# A number that fails is REMOVED, not corrected. The solver treats whatever it is
# given as fact, and no number at all is a smaller error than a confident one.
# ---------------------------------------------------------------------------

Q_SYSTEM = """You audit numbers that were pulled out of a requirements document by
another process. That process was often right about WHERE a number came from and
wrong about WHAT the number measures. Your only job is to catch the second kind of
mistake.

Each item gives you a quantity, what the extraction claims it means, and the
sentence it was taken from. Decide what the number in that sentence actually
measures.

  - capacity means how many units ONE instance of that participant can serve.
      "each charger serves one vehicle at a time"   -> capacity 1. OK.
      "the site draws up to 350 kW"                 -> that is power, not a count
                                                       of things served. FAILS.
  - demand means how many units EACH depending instance consumes from a provider.
      "every vehicle occupies one charge point"     -> demand 1. OK.
  - duration means how long that step takes once it can start.
      "charging completes within 40 minutes"        -> a duration. OK.
      "the depot operates 24 hours"                 -> opening hours, not the
                                                       length of this step. FAILS.
  - deadline means the time by which that participant must finish its own goal.

Rates are the trap. "120 packs per minute" is a rate, and a rate is neither a
capacity nor a duration until it is combined with something else. If the sentence
gives a rate where a count or a time was claimed, that FAILS.

Answer for every item. Be strict: if the sentence does not plainly state the thing
claimed, the verdict is not "ok"."""


Q_USER = """

Audit these extracted quantities against the document.

<document>
{text}
</document>

<claims>
{claims}
</claims>

Answer with JSON only, no preamble. One entry per claim, same order and same ids:

{{"results": [{{"id": "the id you were given",
                "measures": "what the number in that sentence actually measures",
                "verdict": "ok" or "wrong_unit" or "no_number",
                "note": "one short sentence, only when the verdict is not ok"}}]}}"""


def _q_items(spec, trace):
    """Every non-cardinality number, with the sentence it should be supported by."""
    src_a = (trace or {}).get("actors") or {}
    src_d = (trace or {}).get("deps") or {}
    src_g = (trace or {}).get("goals") or {}
    label = {a["type"]: (a.get("label") or a["type"]) for a in spec.get("actors", [])}
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec.get("goals", [])}
    owner = {g["name"]: g["owner"] for g in spec.get("goals", [])}
    items = []
    for a in spec.get("actors", []):
        if a.get("capacity") is not None:
            items.append({"id": "capacity:" + a["type"], "kind": "capacity",
                          "of": label[a["type"]], "value": a["capacity"],
                          "source": src_a.get(a["type"], "(no source recorded)")})
        if a.get("deadline") is not None:
            items.append({"id": "deadline:" + a["type"], "kind": "deadline",
                          "of": label[a["type"]], "value": a["deadline"],
                          "source": src_a.get(a["type"], "(no source recorded)")})
    for g in spec.get("goals", []):
        if g.get("duration") is not None:
            # The goal's OWN sentence, not its owner's. Auditing a duration against
            # the actor's sentence judged it on words that were never about timing,
            # which produced a confident rejection of a number the document gave.
            items.append({"id": "duration:" + g["name"], "kind": "duration",
                          "of": glabel[g["name"]] + " (of "
                                + label.get(owner.get(g["name"]), "?") + ")",
                          "value": g["duration"],
                          "source": (src_g.get(g["name"])
                                     or src_a.get(owner.get(g["name"]))
                                     or "(no source recorded)")})
    for d in spec.get("deps", []):
        if d.get("demand") is not None:
            key = d["from"] + " -> " + d["to"]
            items.append({"id": "demand:" + key, "kind": "demand",
                          "of": glabel.get(d["from"], d["from"]) + " needing "
                                + glabel.get(d["to"], d["to"]),
                          "value": d["demand"],
                          "source": src_d.get(key, "(no source recorded)")})
    return items


def verify_quantities(spec, trace, text, backend="auto", model=None):
    """Audit capacity, demand, duration and deadline. Same contract as verify()."""
    items = _q_items(spec, trace)
    if not items:
        return {"checked": 0, "results": []}

    lines = []
    for it in items:
        lines.append(f'- id: {it["id"]}\n  quantity: {it["kind"]}\n'
                     f'  of: {it["of"]}\n  claimed value: {it["value"]}\n'
                     f'  sentence: "{it["source"]}"')
    prompt = Q_SYSTEM + Q_USER.format(text=text, claims="\n".join(lines))
    out = _ask(prompt, backend, model)
    if not isinstance(out, dict) or "results" not in out:
        raise ExtractionError("The quantity audit returned nothing usable.")
    known = {it["id"] for it in items}
    results = [r for r in (out.get("results") or []) if r.get("id") in known]
    return {"checked": len(items), "results": results}


def apply_quantity_verdicts(spec, results):
    """Remove every quantity that failed its audit. Returns (spec, removed)."""
    bad = {r["id"] for r in results if r.get("verdict") != "ok"}
    why = {r["id"]: r for r in results}
    out = json.loads(json.dumps(spec))
    removed = []

    def drop(container, field, key, what):
        if key in bad and container.get(field) is not None:
            removed.append((key, container[field], what,
                            (why.get(key) or {}).get("verdict"),
                            (why.get(key) or {}).get("measures")))
            container[field] = None

    for a in out.get("actors", []):
        drop(a, "capacity", "capacity:" + a["type"], a.get("label") or a["type"])
        drop(a, "deadline", "deadline:" + a["type"], a.get("label") or a["type"])
    for g in out.get("goals", []):
        drop(g, "duration", "duration:" + g["name"], g.get("label") or g["name"])
    for d in out.get("deps", []):
        drop(d, "demand", "demand:" + d["from"] + " -> " + d["to"],
             d["from"] + " -> " + d["to"])
    return out, removed

# ---------------------------------------------------------------------------
# The structure.
#
# Both audits above check NUMBERS. Nothing checked SHAPE, and shape is what
# every finding is actually made of. "Line Controller is present and unable to
# meet its goal" does not come from a count, it comes from a dependency: the
# controller cannot finish unless at least one capping unit reports. Invent that
# dependency and you invent the defect. Miss it and you miss the one the customer
# is paying for.
#
# Experiment A measured citations (honest) and numbers (not). Nobody had ever
# measured the graph. This asks the same narrow kind of question that made the
# other two audits work:
#
#     does this sentence say the depender cannot succeed without the provider?
#
# An unsupported dependency is FLAGGED AND KEPT. It used to be removed, on the
# reasoning that removal makes the model claim less and is therefore the safe
# direction for an assertion nobody can trace to a sentence.
#
# The first real in-scope document overturned that. On an 83 page utility
# specification the audit removed 9 of 26 dependencies, every one of them
# engineering-obvious but stated across several sentences rather than one: three
# protection IEDs depending on the trip circuit, the busbar protection and the
# gateway depending on the station switch, the event list depending on GPS time.
# Removing them removed the structure that produces findings, and the analysis
# came back 3,456 configurations, 128 classes and ZERO problems.
#
# So "claims less" was not the safe direction. It produced a clean bill of health
# for a substation specification, which is the most dangerous output this tool
# can emit. The rule now matches the breakdown audit, and the reason is general:
# A FALSE ALARM IS INSPECTABLE AND SILENCE IS NOT. A flagged dependency that is
# wrong produces a finding the reader can trace back to a sentence and dismiss.
# A removed one produces nothing for anybody to check.
# ---------------------------------------------------------------------------

S_SYSTEM = """You audit dependencies that another process pulled out of a
requirements document. Each one claims that one participant cannot achieve
something without another participant doing its part.

For each item you get the claim, its multiplicity, and the sentence it was drawn
from. Decide whether the DOCUMENT states that dependency.

Read the sentence in its place in the document rather than on its own. A
specification establishes a dependency across a clause here and a table there,
and an earlier version of this audit judged each claim against its one sentence
and rejected nine real dependencies out of twenty six on an 83 page utility
specification. Removing them made that specification come back with no problems
at all. Look around the quote before you reject it.

Then be strict about what a dependency is. Every one of the following was drawn
out of a real specification as a dependency and none of them is one.

  AN ALTERNATIVE, and this is the one that has actually cost this tool a false
  defect. "Additional multifunction meter may be provided for monitoring the
  measurement, if monitoring of measurement is not available in the bay unit"
  says the meter appears WHEN THE BAY UNIT DOES NOT do the job itself. It does
  not say the bay unit needs the meter. Read the wrong way round it proves that
  the bay unit can be present and unable to meet its goal, which the document
  never says. Whenever the sentence carries "if not available", "where not
  provided", "in the absence of", "as a fallback", or "alternatively", work out
  which way the need runs before you accept it.

  A CONNECTION. "The relays shall be connected to the Ethernet switch", "the
  gateway shall interface with the IEDs". That is wiring and protocol. It does
  not state that either one fails at its own goal without the other.

  A LIST. Both participants named in one sentence, one table or one scope of
  supply, with nothing said about needing.

  AN OPTION. "may be provided", "where specified by the purchaser", with nothing
  stated to depend on it.

  SOUND ENGINEERING THE DOCUMENT NEVER STATES. A protection relay obviously
  needs its trip circuit. If the document does not say so, the dependency is
  unsupported, and it is not your job to supply the reasoning the specification
  left out.

Multiplicity means:
  1..*   the depender needs AT LEAST ONE of the providers to do its part.
         "the controller shall only consider a bottle filled once at least one
          filling head reports it"                             -> 1..*
  *..*   the depender needs EVERY provider that is present, or none at all.
         "a run may only start when all fitted cappers report ready"  -> *..*

Verdicts:
  ok           the document states this dependency, with this multiplicity
  wrong_mult   the dependency is real but the multiplicity is the other one.
               Give the correct one in `correct_mult`.
  unsupported  the document does not state it. Use this for every case in the
               list above, and whenever the sentence merely mentions both
               participants or describes what one of them does without making
               the other depend on it.

An unsupported dependency is kept in the model and reported, so saying so costs
the reader a paragraph to check. A real dependency you call unsupported takes
the finding it carries down with it. Both mistakes are real and neither one is
the safe answer.

House style: never use em dashes or en dashes. Use a comma or a full stop instead."""

S_SYSTEM_BEFORE_STRICT = """You audit dependencies that another process pulled out of a
requirements document. Each one claims that one participant cannot achieve
something without another participant doing its part.

For each item you get the claim, its multiplicity, and the sentence it was taken
from. Decide whether that sentence really states that dependency.

Multiplicity means:
  1..*   the depender needs AT LEAST ONE of the providers to do its part.
         "the controller shall only consider a bottle filled once at least one
          filling head reports it"                             -> 1..*
  *..*   the depender needs EVERY provider that is present, or none at all.
         "a run may only start when all fitted cappers report ready"  -> *..*

Verdicts:
  ok           the sentence states this dependency, with this multiplicity
  wrong_mult   the dependency is real but the multiplicity is the other one.
               Give the correct one in `correct_mult`.
  unsupported  the sentence does not state this dependency at all. Use this when
               the sentence merely mentions both participants, or describes what
               one of them does without making the other depend on it.

Be strict about `unsupported`, and just as strict about not using it when the
dependency plainly is stated. A dependency wrongly removed hides a real defect,
and one wrongly kept invents a defect that is not there."""

S_USER = """

Audit these extracted dependencies against the document.

<document>
{text}
</document>

<claims>
{claims}
</claims>

Answer with JSON only, no preamble. One entry per claim, same ids:

{{"results": [{{"id": "the id you were given",
                "verdict": "ok" or "wrong_mult" or "unsupported",
                "correct_mult": "1..*" or "*..*", only when verdict is wrong_mult,
                "why": "one short sentence, only when the verdict is not ok"}}]}}"""


def verify_structure(spec, trace, text, backend="auto", model=None, only=None):
    """Audit every dependency against the sentence it was drawn from.

    `only` restricts the pass to the given "from -> to" keys. Same prompt, same
    document, same claim format, just a smaller list. It exists so the edges the
    RECALL audit added can be put through this stricter reading without re-judging
    the ones already judged. Re-judging them is not harmless: on ElectraNet a second
    run of this pass flipped an edge from `unsupported` back to `ok` with nothing
    about the edge changed, which would have quietly erased a mark a finding rested
    on. A pass this movable may add doubt to a claim. It may not remove it.
    """
    deps = spec.get("deps", [])
    if only is not None:
        want = set(only)
        deps = [d for d in deps if d["from"] + " -> " + d["to"] in want]
    if not deps:
        return {"checked": 0, "results": []}

    src = (trace or {}).get("deps") or {}
    owner = {g["name"]: g["owner"] for g in spec.get("goals", [])}
    label = {a["type"]: (a.get("label") or a["type"]) for a in spec.get("actors", [])}
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec.get("goals", [])}

    lines = []
    for d in deps:
        key = d["from"] + " -> " + d["to"]
        dep_actor = label.get(owner.get(d["from"]), "?")
        prov_actor = label.get(owner.get(d["to"]), "?")
        lines.append(
            f'- id: {key}\n'
            f'  claim: {dep_actor} cannot achieve "{glabel.get(d["from"], d["from"])}" '
            f'without {prov_actor} doing "{glabel.get(d["to"], d["to"])}"\n'
            f'  multiplicity: {d.get("mult")}\n'
            f'  sentence: "{str(src.get(key, "(no source recorded)"))[:400]}"')

    out = _ask(S_SYSTEM + S_USER.format(text=text, claims="\n".join(lines)),
               backend, model)
    if not isinstance(out, dict) or "results" not in out:
        raise ExtractionError("The structure audit returned nothing usable.")
    known = {d["from"] + " -> " + d["to"] for d in deps}
    out["results"] = [r for r in out["results"] if r.get("id") in known]
    out["checked"] = len(deps)
    return out


def apply_structure_verdicts(spec, results):
    """Correct multiplicities, flag unsupported dependencies, remove nothing.

    Returns (spec, fixed, flagged). A corrected multiplicity is applied because it
    arrives with the right value beside it and the change is local. An unsupported
    dependency stays in the model and is reported, so the reader sees both the
    finding it produces and the fact that no single sentence states it.

    The flag is written ONTO the dependency, not only into the returned list. The
    list is a report of what this pass did and it stops here. The mark travels with
    the model, which is what lets `analyze.provenance` carry it forward to the
    findings that rest on this edge. Without the mark the flag reached a banner and
    the finding built on the same edge was published as proved.
    """
    by = {r.get("id"): r for r in results if isinstance(r, dict)}
    out = json.loads(json.dumps(spec))
    fixed, flagged = [], []
    for d in out.get("deps", []):
        key = d["from"] + " -> " + d["to"]
        r = by.get(key) or {}
        verdict = r.get("verdict", "ok")
        if verdict == "wrong_mult" and r.get("correct_mult") in ("1..*", "*..*"):
            if r["correct_mult"] != d.get("mult"):
                fixed.append((key, "multiplicity", d.get("mult"),
                              r["correct_mult"], r.get("why")))
                d["mult"] = r["correct_mult"]
        elif verdict == "unsupported":
            flagged.append((key, "unsupported", d.get("mult"), None, r.get("why")))
            d["flagged"] = "unsupported"
            d["flag_why"] = r.get("why") or ""
    return out, fixed, flagged

# ---------------------------------------------------------------------------
# What the extraction MISSED.
#
# The three audits above all verify what is present: is this bound supported,
# does this number measure what it claims, does this dependency exist in the
# text. Every one of them is blind to an omission. A participant the extraction
# never noticed, or a dependency it never drew, is invisible to all three, and
# the report then says "no problems found" with total confidence.
#
# That is the more dangerous direction. An invention produces a false alarm the
# customer can argue with. An omission produces a clean bill of health for a
# system that has a defect in it.
#
# So this pass reads the document against the model and asks what is in one and
# not the other. NOTHING IS ADDED TO THE MODEL. A new participant would need
# goals, a root and bounds, none of which a second opinion should be inventing,
# and the standing rule is that the AI proposes and never decides. The result is
# reported as "what this analysis may have missed", which is also the review aid
# the tool has always needed.
# ---------------------------------------------------------------------------

R_SYSTEM = """You are checking whether a model built from a requirements document
left anything out. You are given the document and the list of participants and
dependencies that were extracted from it.

Report only what the document genuinely describes and the model does not contain.

A PARTICIPANT is a kind of machine, component or system that takes part in the
work, and whose number could vary between one build and another. Do not report
people or roles. Do not report the system as a whole. Do not report something the
document merely mentions in passing, such as a standard it complies with or a
place where it is installed.

Measured on real documents, these are the wrong answers that come up most, and
none of them is a participant:
  - DATA the system holds. An entry, a record, a group, a file of settings. A
    database with 400 entries is one database.
  - a CHOICE or setting. An encryption algorithm, a protocol, a mode of operation.
  - a piece of the software's own internals that does no work of its own, such as
    a dialog, a screen or a menu.
Ask whether it is a thing that could be missing from a delivered system and would
stop something else from working. If not, leave it out.

A DEPENDENCY is a statement that one participant cannot achieve something without
another participant doing its part. It has to be stated, not merely plausible.
"The controller shall only consider a bottle filled once at least one filling head
reports it" is a dependency. "The line contains filling heads and cappers" is not.

Be conservative. A wrong omission report sends an engineer looking for something
that is not there, and costs the report its credibility. If the document does not
plainly describe it, leave it out. Reporting nothing is a perfectly good answer
and is the correct one for a well extracted model."""

R_USER = """

Check this model against the document it came from.

<document>
{text}
</document>

<model>
{model}
</model>

Answer with JSON only, no preamble:

{{"missing_actors": [{{"name": "what the document calls it",
                       "sentence": "the sentence that describes it",
                       "why": "one short sentence on why it is a participant"}}],
  "missing_deps":   [{{"depender": "participant that needs help",
                       "provider": "participant that provides it",
                       "sentence": "the sentence that states it",
                       "why": "one short sentence"}}]}}

Empty lists are the right answer when nothing was missed."""


def _model_summary(spec):
    label = {a["type"]: (a.get("label") or a["type"]) for a in spec.get("actors", [])}
    owner = {g["name"]: g["owner"] for g in spec.get("goals", [])}
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec.get("goals", [])}
    lines = ["PARTICIPANTS"]
    for a in spec.get("actors", []):
        lines.append(f'- {label[a["type"]]} ({a["lo"]}..{a["hi"]})')
    lines.append("")
    lines.append("DEPENDENCIES")
    if not spec.get("deps"):
        lines.append("- none")
    for d in spec.get("deps", []):
        lines.append(f'- {label.get(owner.get(d["from"]), "?")} needs '
                     f'"{glabel.get(d["to"], d["to"])}" from '
                     f'{label.get(owner.get(d["to"]), "?")} ({d.get("mult")})')
    return "\n".join(lines)


def verify_recall(spec, trace, text, backend="auto", model=None):
    """What the document describes that the model does not contain. Never applied."""
    out = _ask(R_SYSTEM + R_USER.format(text=text, model=_model_summary(spec)),
               backend, model)
    if not isinstance(out, dict):
        raise ExtractionError("The completeness audit returned nothing usable.")
    return {"missing_actors": out.get("missing_actors") or [],
            "missing_deps": out.get("missing_deps") or []}


# ---------------------------------------------------------------------------
# The structure INSIDE an actor.
#
# `verify_structure` audits the dependencies between actors. This audits the
# breakdown within one: whether a goal needs ALL of its sub-goals, at least one,
# or exactly one. That operator decides satisfaction exactly as multiplicity does
# across actors, and nothing checked it. Nor did anything check which goal is the
# ROOT, which is what "this participant is satisfied" even means.
#
# The action rule here is DELIBERATELY different from the dependency audit, and
# the difference is not an oversight. Removing an unsupported dependency makes
# the model claim LESS, which is the safe direction for an assertion. Removing a
# decomposition makes a goal a leaf, which makes it trivially satisfiable and
# therefore makes the model claim FEWER DEFECTS. That direction hides exactly
# what the customer is paying to find, so a wrong operator is corrected, and
# anything unsupported is reported for review rather than rewritten.
# ---------------------------------------------------------------------------

D_SYSTEM = """You audit the internal structure of a goal model that another
process pulled out of a requirements document.

Two kinds of item.

A BREAKDOWN says a goal is met by meeting its sub-goals, in one of three ways:
  AND  every sub-goal is needed
  OR   at least one sub-goal is enough
  XOR  exactly one of exactly two, and never both

A ROOT says which goal is the thing a participant must achieve overall. Everything
else it does is in service of that.

For each item, decide from the sentence given whether the claim is right.

  ok            the sentence supports this
  wrong_op      it is a breakdown of the other kind. Give `correct_op`.
  wrong_root    a different goal from the list is the overall one. Give `correct`.
  unsupported   the sentence does not establish this at all

The difference between AND and OR is the difference between "the run is complete
when the bottles are filled, capped AND palletised" and "the operator may stop the
line from the panel OR the pendant". Read the sentence, not the plausibility."""

D_USER = """

Audit this model's internal structure against the document.

<document>
{text}
</document>

<claims>
{claims}
</claims>

Answer with JSON only, no preamble. One entry per claim, same ids:

{{"results": [{{"id": "the id you were given",
                "verdict": "ok" or "wrong_op" or "wrong_root" or "unsupported",
                "correct_op": "AND" or "OR" or "XOR", only when verdict is wrong_op,
                "correct": "the goal name", only when verdict is wrong_root,
                "why": "one short sentence, only when the verdict is not ok"}}]}}"""


def verify_decomposition(spec, trace, text, backend="auto", model=None):
    """Audit every breakdown operator and every root goal."""
    decomp = spec.get("decomp", [])
    actors = spec.get("actors", [])
    if not decomp and not actors:
        return {"checked": 0, "results": []}

    src_d = (trace or {}).get("decomp") or {}
    src_a = (trace or {}).get("actors") or {}
    src_g = (trace or {}).get("goals") or {}
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec.get("goals", [])}
    label = {a["type"]: (a.get("label") or a["type"]) for a in actors}
    owned = {}
    for g in spec.get("goals", []):
        owned.setdefault(g["owner"], []).append(g["name"])

    lines = []
    for d in decomp:
        kids = ", ".join(f'"{glabel.get(c, c)}"' for c in d.get("children", []))
        lines.append(
            f'- id: op:{d["parent"]}\n'
            f'  claim: "{glabel.get(d["parent"], d["parent"])}" is met by {d.get("op")} '
            f'of {kids}\n'
            f'  sentence: "{str(src_d.get(d["parent"], "(no source recorded)"))[:400]}"')
    roots = spec.get("roots") or {}
    for t, rootgoal in roots.items():
        others = ", ".join(f'"{glabel.get(n, n)}" ({n})'
                           for n in owned.get(t, []) if n != rootgoal) or "none"
        lines.append(
            f'- id: root:{t}\n'
            f'  claim: what {label.get(t, t)} must achieve overall is '
            f'"{glabel.get(rootgoal, rootgoal)}" ({rootgoal})\n'
            f'  its other goals: {others}\n'
            f'  sentence: "{str(src_g.get(rootgoal) or src_a.get(t) or "(no source recorded)")[:400]}"')

    out = _ask(D_SYSTEM + D_USER.format(text=text, claims="\n".join(lines)),
               backend, model)
    if not isinstance(out, dict) or "results" not in out:
        raise ExtractionError("The structure audit returned nothing usable.")

    # The extraction labels its own inferences with "implied:", and nothing read
    # that label until now. It changes what a flag MEANS: not "the audit disputes
    # the document" but "the extraction said it was inferring, and the audit
    # confirms no sentence states it". The auditor sometimes says so in prose and
    # sometimes does not, so it is established here instead of hoped for.
    implied, single = {}, set()
    for d in decomp:
        key = "op:" + d["parent"]
        implied[key] = str(src_d.get(d["parent"], "")).strip().lower().startswith("implied:")
        if len(d.get("children") or []) == 1:
            single.add(key)
    for t, rootgoal in roots.items():
        implied["root:" + t] = str(
            src_g.get(rootgoal) or src_a.get(t) or "").strip().lower().startswith("implied:")
    for r in out["results"]:
        if isinstance(r, dict):
            r["was_implied"] = bool(implied.get(r.get("id")))
            r["single_child"] = r.get("id") in single

    out["checked"] = len(lines)
    return out


def apply_decomposition_verdicts(spec, results):
    """Correct wrong operators. Report everything else. Returns (spec, fixed, flagged).

    Only the operator is rewritten, because a wrong operator arrives with the
    right one beside it and the change is local. A root or a breakdown the
    document does not support is FLAGGED, never removed: dropping it would make
    the model easier to satisfy and would therefore hide defects.

    As with the dependency audit, the flag is written ONTO the model and not only
    into the returned list. A breakdown carries it on its own entry, a root carries
    it on the actor whose root it is, and `analyze.provenance` walks the goal tree
    from there to the findings that rest on them. The returned list is a report of
    what this pass did and it stops here.
    """
    by = {r.get("id"): r for r in results if isinstance(r, dict)}
    out = json.loads(json.dumps(spec))
    fixed, flagged = [], []
    for d in out.get("decomp", []):
        r = by.get("op:" + d["parent"]) or {}
        v = r.get("verdict", "ok")
        if v == "wrong_op" and r.get("correct_op") in ("AND", "OR", "XOR") \
                and r["correct_op"] != d.get("op"):
            fixed.append((d["parent"], d.get("op"), r["correct_op"], r.get("why")))
            d["op"] = r["correct_op"]
        elif v not in ("ok", "wrong_op"):
            note = r.get("why") or ""
            if r.get("was_implied"):
                note = ("The extraction marked this as inferred rather than quoted, "
                        "and the audit confirms no sentence states it. " + note)
            if r.get("single_child"):
                note += (" It also breaks a goal into one sub-goal, which adds a level "
                         "without adding a condition.")
            flagged.append(("breakdown", d["parent"], v, note.strip()))
            d["flagged"] = v
            d["flag_why"] = note.strip()
    by_type = {a["type"]: a for a in out.get("actors", [])}
    for t in (out.get("roots") or {}):
        r = by.get("root:" + t) or {}
        if r.get("verdict", "ok") not in ("ok",):
            why = ((r.get("why") or "") +
                   (f" Suggested: {r.get('correct')}" if r.get("correct") else ""))
            flagged.append(("root", t, r.get("verdict"), why))
            # On the actor, because "which goal is this participant's overall one"
            # is a claim about the actor. Every finding about it says the actor
            # cannot meet ITS GOAL, so a doubtful root puts the whole sentence in
            # doubt rather than one branch of the tree.
            if t in by_type:
                by_type[t]["root_flagged"] = r.get("verdict")
                by_type[t]["root_flag_why"] = why.strip()
    return out, fixed, flagged

# ---------------------------------------------------------------------------
# The minimum.
#
# `verify()` above audits the claimed MAXIMUM. Nothing audited the minimum, and
# the minimum is the number that decides whether there is a finding at all. The
# sensitivity probe in gaps.py says it in those words: whether any exist changes
# the result, the maximum usually does not. `lo = 0` means the specification
# permits a system built with none of these, which is what produces "present and
# unable to do its job". `lo = 1` means there is nothing to find.
#
# Two readings of the same 83 page specification disagreed on exactly this field:
# distance protection 0..2 against 1..2, restricted earth fault 0..2 against
# 1..1, backup over-current 1..2 against 1..1. Participants agreed 90% of the
# time, the maximum mostly agreed, and the findings agreed 0% of the time. The
# unaudited field was the unstable one, and it was the one that mattered.
#
# When the document does not say, the analysis assumes the thing CAN be absent
# and the gap report says so. That follows the rule the dependency audit already
# established: a false alarm can be traced to a sentence and dismissed, silence
# cannot be inspected.
# ---------------------------------------------------------------------------

M_SYSTEM = """You audit one thing about each participant in a system: whether the
document says it must always be present, or allows it to be absent.

You are given the participant, what the extraction assumed, and the sentence it
came from. Read the sentence and answer:

  always_present   the document requires at least one at all times.
                   "The line is supervised by a single line controller"     -> yes
                   "Each bay shall be provided with a bay control unit"     -> yes
  may_be_absent    the document allows there to be none, or describes it as
                   optional, or as fitted only in some variants.
                   "Bus-bar protection shall be provided where specified"   -> yes
                   "Up to three filling heads" with no stated minimum       -> yes
  no_statement     the document simply does not say either way.

The difference between "shall be provided" and "may be provided" decides this,
and so does an upper bound with no lower one: "up to four" says nothing about
whether zero is allowed.

Do not reason about what would be sensible engineering. A protection relay that
any competent designer would always fit is still `no_statement` if the document
never says so. What is being audited is the document, not the practice."""

M_USER = """

Audit these minimums against the document.

<document>
{text}
</document>

<claims>
{claims}
</claims>

Answer with JSON only, no preamble. One entry per claim, same names:

{{"results": [{{"actor": "the name you were given",
                "verdict": "always_present" or "may_be_absent" or "no_statement",
                "quote": "the words that decide it, or empty when no_statement",
                "note": "one short sentence, only when the verdict is not what was assumed"}}]}}"""


# ---------------------------------------------------------------------------
# The maximum, which nothing audited even after the minimum was fixed.
#
# `verify_minimums` anchored `lo` and it worked. Measured across four readings of
# one 83 page specification: `lo` agrees 93% of the time and `lo_stated` agrees on
# 17 of 17 participants, a clean 100%.
#
# `hi` never got the same treatment, and the same measurement says so. `hi` agrees
# 67% of the time and `hi_stated` agrees on 12 of 17, a 71%. Same field type, same
# document, same two readings, and the only difference between them is that one has
# an audit behind it and the other does not.
#
# That flag is not a detail. `gaps.build` raises a cardinality gap exactly when
# `hi_stated` is False, so it decides what appears in the deliverable. Asked about
# the SAME document, one reading said the maximum was unstated for 50% of the
# participants and another said 90%, and the gap counts followed them, 14 against
# 21. The gap report's headline number moves because this flag moves.
#
# Assume nothing when the document is silent. `hi_stated: False` leaves the bound
# where the extraction put it and lets the gap report ask the reader for it, which
# is the rule the minimum audit already follows. Inventing an upper bound would hand
# the solver a number nobody wrote down.
# ---------------------------------------------------------------------------

X_SYSTEM = """You audit one thing about each participant in a system: whether the
document states an upper bound on how many of them there can be.

You are given the participant, the maximum the extraction assumed, and the sentence
it came from. Read the document and answer:

  stated        the document gives an upper bound, in words or figures. Give the
                number in `count`.
                "up to four filling heads"                      -> stated, 4
                "a maximum of six cells"                        -> stated, 6
                "one battery set is common to both inverters"   -> stated, 1
                "each bay shall have one bay control unit"      -> stated, 1
  no_statement  the document does not say how many there can be. A plural with no
                number is NOT a bound.
                "protection relays shall be provided"           -> no_statement
                "multiple display units"                        -> no_statement
                "as required by the site"                       -> no_statement

Three traps, all of them seen on real specifications.

A number that counts something ELSE is not a bound on this participant. "The
equipment offered shall have six output ports" bounds PORTS, not clocks. "A database
of 400 entries" bounds entries, not databases. If the number counts anything other
than how many of THIS participant a system may contain, answer no_statement.

A quantity for ONE named installation is not a bound on the type. A tender listing
exactly the panels for one substation is describing a delivery, not a rule about how
many may be present. Answer stated only if the document is plainly fixing the number
for any build. When it reads as a bill of materials for one project, answer
no_statement and say so in the note.

A capability is not a count. "Supports up to 32 devices" describes what one unit can
handle, which is capacity, not how many of that unit exist.

Do not reason about what would be sensible engineering. A component any competent
designer would fit exactly once is still no_statement if the document never says so.
What is being audited is the document, not the practice."""

X_USER = """

Audit these maximums against the document.

<document>
{text}
</document>

<claims>
{claims}
</claims>

Answer with JSON only, no preamble. One entry per claim, same names:

{{"results": [{{"actor": "the name you were given",
                "verdict": "stated" or "no_statement",
                "count": the upper bound as an integer, only when stated,
                "quote": "the words that give it, or empty when no_statement",
                "note": "one short sentence, only when this differs from what was assumed"}}]}}"""


def verify_maximums(spec, trace, text, backend="auto", model=None):
    """Audit `hi` for every participant. The twin of `verify_minimums`.

    Every actor is asked about, not only the ones the extraction already doubted,
    because the FLAG is what moves. An extraction that wrongly believes the document
    gave it a number never sets `hi_stated: False`, so the gap is never raised and
    nothing downstream can notice it is missing.
    """
    actors = spec.get("actors", [])
    if not actors:
        return {"checked": 0, "results": []}
    src = (trace or {}).get("actors") or {}
    lines = []
    for a in actors:
        claimed = ("the document gives %s" % a.get("hi") if a.get("hi_stated")
                   else "no upper bound was found, %s was assumed" % a.get("hi"))
        lines.append('- actor: %s\n'
                     '  called: %s\n'
                     '  the extraction assumed: %s\n'
                     '  taken from: "%s"'
                     % (a["type"], a.get("label") or a["type"], claimed,
                        str(src.get(a["type"], "(no source recorded)"))[:400]))
    out = _ask(X_SYSTEM + X_USER.format(text=text, claims="\n".join(lines)),
               backend, model)
    if not isinstance(out, dict) or "results" not in out:
        raise ExtractionError("The maximum audit returned nothing usable.")
    known = {a["type"] for a in actors}
    out["results"] = [r for r in out["results"] if r.get("actor") in known]
    out["checked"] = len(actors)
    return out


def apply_maximum_verdicts(spec, results):
    """Set `hi` and `hi_stated` from the document. Returns (spec, changed, unstated).

    `no_statement` does NOT invent a bound. It leaves `hi` where the extraction put
    it and records `hi_stated: False` so the gap report asks the reader for it. That
    is the rule the minimum audit already follows, and it is why the product reports
    absences rather than filling them in.

    A stated count is applied, because it arrives with the number beside it and the
    change is local. It is refused when it would put the maximum below the minimum,
    since that is a contradiction rather than a correction.
    """
    by = {r.get("actor"): r for r in results if isinstance(r, dict)}
    out = json.loads(json.dumps(spec))
    changed, unstated, refused = [], [], []
    for a in out.get("actors", []):
        r = by.get(a["type"])
        if not r:
            continue
        old, label = a.get("hi"), (a.get("label") or a["type"])
        if r.get("verdict") == "stated":
            try:
                n = int(r.get("count"))
            except (TypeError, ValueError):
                n = None
            if n is not None and n < int(a.get("lo", 0)):
                # The document appears to give a maximum BELOW the audited minimum.
                # One of the two is wrong and this pass cannot tell which. Recording
                # it as stated would suppress the gap and the contradiction would
                # vanish, so it is left unstated, which makes the gap report ask for
                # the number, and it is returned so the run can say what happened.
                a["hi_stated"] = False
                refused.append((label, old, n, int(a.get("lo", 0))))
                continue
            a["hi_stated"] = True
            if n is None or n == old:
                continue
            a["hi"] = n
            changed.append((label, old, n, r.get("quote")))
        else:
            a["hi_stated"] = False
            unstated.append((a["type"], label))
    return out, changed, unstated, refused


def verify_minimums(spec, trace, text, backend="auto", model=None):
    """Audit `lo` for every participant. The field that decides whether findings exist."""
    actors = spec.get("actors", [])
    if not actors:
        return {"checked": 0, "results": []}
    src = (trace or {}).get("actors") or {}
    lines = []
    for a in actors:
        assumed = ("at least one is always present" if int(a.get("lo", 0)) >= 1
                   else "it may be absent")
        lines.append(f'- actor: {a["type"]}\n'
                     f'  called: {a.get("label") or a["type"]}\n'
                     f'  the extraction assumed: {assumed}\n'
                     f'  taken from: "{str(src.get(a["type"], "(no source recorded)"))[:400]}"')
    out = _ask(M_SYSTEM + M_USER.format(text=text, claims="\n".join(lines)), backend, model)
    if not isinstance(out, dict) or "results" not in out:
        raise ExtractionError("The minimum audit returned nothing usable.")
    known = {a["type"] for a in actors}
    out["results"] = [r for r in out["results"] if r.get("actor") in known]
    out["checked"] = len(actors)
    return out


def apply_minimum_verdicts(spec, results):
    """Set `lo` from the document. Returns (spec, changed, unstated).

    `no_statement` leaves the participant able to be absent, and records
    `lo_stated: False` so the gap report can ask for it. Assuming presence would
    silence a finding on the strength of something the document never said.
    """
    by = {r.get("actor"): r for r in results if isinstance(r, dict)}
    out = json.loads(json.dumps(spec))
    changed, unstated = [], []
    for a in out.get("actors", []):
        r = by.get(a["type"])
        if not r:
            continue
        want = r.get("verdict")
        old = int(a.get("lo", 0))
        if want == "always_present":
            a["lo"], a["lo_stated"] = 1, True
        elif want == "may_be_absent":
            a["lo"], a["lo_stated"] = 0, True
        else:
            a["lo"], a["lo_stated"] = 0, False
            unstated.append((a["type"], a.get("label") or a["type"]))
        if a["hi"] < a["lo"]:
            a["hi"] = a["lo"]
        if a["lo"] != old:
            changed.append((a.get("label") or a["type"], old, a["lo"],
                            want, r.get("quote")))
    return out, changed, unstated


# ---------------------------------------------------------------------------
# The dependency that was never drawn.
#
# `verify_minimums` fixed `lo`, and a fresh pair of readings of the same 83 page
# specification proved it: both readings agreed the Additional multifunction
# measurement meter is 0..1 with the minimum STATED. The field that used to move
# no longer moves.
#
# The findings still agreed 0% of the time. One reading proved two defects and
# the other proved none, and the whole difference was one edge:
#
#     Bay Control & Protection Unit (33 kV bay)
#         -> Additional multifunction measurement meter, 1..*
#
# The second reading drew it and both of its findings rest on it. The first
# reading never drew any dependency into the meter at all, so the meter carried a
# bare root goal, nothing could be blocked, and the report said no problems found.
# No edge, no defect.
#
# That is the same shape of failure as the minimum, one layer down. Each repair
# exposes the next unaudited field: `hi` was audited so the movement sat in `lo`,
# `lo` is audited so the movement sits in whether the EDGE EXISTS AT ALL. Every
# audit above this one judges what is present. `verify_recall` is the only pass
# that looks for omissions and it is reported, never applied, so an edge it finds
# changes no finding.
#
# So this one applies. It is deliberately narrower than `verify_recall`: it
# proposes no participants, only dependencies between participants the model
# already has, expressed in goal names the model already contains. Nothing is
# invented, an edge is either recovered or it is not.
#
# ADDING makes the model claim MORE, which is the direction the house rule calls
# unsafe, so the rule is not waived, it is paid for:
#   - two passes, propose then confirm, and only a confirmed edge is applied,
#   - every applied edge carries the sentence that supports it, in the trace,
#     exactly like an extracted one, so a reader can check it,
#   - every applied edge is marked `added`, and the report says so, so a finding
#     that rests on a recovered edge is never presented as if the extraction
#     found it.
# The precedent is `apply_structure_verdicts`, which stopped removing unsupported
# edges once removal produced a clean bill of health for a substation. A false
# alarm is inspectable and silence is not, and that argument runs in both
# directions.
# ---------------------------------------------------------------------------

MAX_PROPOSALS = 40

DR_SYSTEM = """You are looking for dependencies that a requirements document
states and a model built from it does not contain.

A DEPENDENCY is a statement that one participant cannot achieve something without
another participant doing its part. It has to be stated by the document, not
merely plausible engineering.
  "the controller shall only consider a bottle filled once at least one filling
   head reports it"                                        -> a dependency
  "the line contains filling heads and cappers"            -> not a dependency

The statement does not have to sit in one sentence. A specification usually
establishes a dependency across a clause here and a table there, and an earlier
pass that judged each candidate against a single sentence rejected nine real
dependencies out of twenty six on one document. Read the neighbourhood. What you
may not do is supply the reasoning yourself. If the document never says the one
needs the other, there is no dependency, however obvious it looks to an engineer.

You are given the participants, every goal each one owns, and the dependencies
already in the model. Propose only edges that are NOT already there.

Express each edge in the goal names you were given, exactly as spelt. The
depending goal must belong to one participant and the depended-on goal to a
different one. When no particular goal of the provider is the right target, use
that participant's root goal, which is marked.

Multiplicity:
  1..*   the depender needs AT LEAST ONE of the providers to do its part
  *..*   the depender needs EVERY provider that is present to do its part

Missing an edge hides a real defect, so look properly. Inventing one invents a
defect, so quote the words that state it. Propose nothing when the model already
has the dependencies the document states, which is a good answer and a common one.

House style: never use em dashes or en dashes. Use a comma or a full stop instead."""

DR_USER = """

Find dependencies this model is missing.

<document>
{text}
</document>

<model>
{model}
</model>

Answer with JSON only, no preamble:

{{"missing": [{{"from": "the depending goal, exactly as spelt in the model",
                "to": "the depended-on goal, owned by a different participant",
                "mult": "1..*" or "*..*",
                "quote": "the words in the document that state it",
                "why": "one short sentence"}}]}}

An empty list is the right answer when nothing is missing."""

DC_SYSTEM = """You are confirming dependencies that a previous pass proposed
adding to a model of a requirements document. The previous pass was looking for
what was missed, so it was told to look hard. Your job is the opposite one.

For each proposal you get the claim, its multiplicity, and the words the previous
pass quoted in support. Decide against the document:

  supported     the document states that the depender cannot achieve that goal
                unless the provider does its part. The quote, read with the text
                around it, says so.
  wrong_mult    the dependency is stated but the other multiplicity is right.
                Give the correct one in `correct_mult`.
  unsupported   the document does not state it. Use this when the quote merely
                mentions both participants, or describes what one of them does
                without making the other depend on it, or when the connection is
                sound engineering that the document never actually states.

An edge you confirm will be added to the model and may produce a defect report
that goes to an engineer, so confirm only what the document says. An edge you
reject stays out and any defect resting on it stays hidden, so do not reject one
the document plainly states. Both mistakes are real and neither is the safe one.

House style: never use em dashes or en dashes. Use a comma or a full stop instead."""

DC_USER = """

Confirm or reject these proposed dependencies against the document.

<document>
{text}
</document>

<proposals>
{claims}
</proposals>

Answer with JSON only, no preamble. One entry per proposal, same ids:

{{"results": [{{"id": "the id you were given",
                "verdict": "supported" or "wrong_mult" or "unsupported",
                "correct_mult": "1..*" or "*..*", only when verdict is wrong_mult,
                "quote": "the words that decide it, when supported",
                "why": "one short sentence, only when the verdict is not supported"}}]}}"""


# The proposal pass above sweeps the whole model, and on the OPTCL specification it
# swept past the thing it was built for. It recovered five real edges and the
# analysis still proved nothing, because a "present and unable to do its job"
# finding can only come from a provider the document allows to be ABSENT, and two
# of the three such participants had no edge into them at all. A general question
# spread its attention over twenty participants and fifteen that cannot produce a
# finding took most of it.
#
# So this asks the narrow version, which is what worked for the minimum: here are
# the participants that may be absent, what does the document say needs them. It
# is the same question the solver asks, put to the reader of the document.

DA_SYSTEM = """You are given a requirements document and a list of participants
that the document allows to be ABSENT. For each one, find what in the rest of the
system cannot do its job without it.

That is the only question here. You are not looking for what the absent
participant does, you are looking for who NEEDS it, and for the words in the
document that say so.

  "Where the bay control unit does not provide measurement, an additional
   multifunction meter shall be provided"
      -> the bay control unit's measurement goal needs the meter. A dependency.
  "An additional multifunction meter may be provided in the control room"
      -> nothing is said to need it. Not a dependency.

Answer in the goal names you are given, exactly as spelt. The depending goal
belongs to some other participant, and the depended-on goal belongs to the absent
one, usually its root goal, which is marked.

Multiplicity:
  1..*   the depender needs AT LEAST ONE of them to do its part
  *..*   the depender needs EVERY one that is present to do its part

Report nothing for a participant the document never makes anything depend on.
That is a normal answer and it is better than a guess.

House style: never use em dashes or en dashes. Use a comma or a full stop instead."""

DA_USER = """

These participants may be absent. Find what needs them.

<document>
{text}
</document>

<may_be_absent>
{absent}
</may_be_absent>

<the_rest_of_the_model>
{model}
</the_rest_of_the_model>

Answer with JSON only, no preamble:

{{"missing": [{{"from": "the depending goal, owned by another participant",
                "to": "the goal of the participant that may be absent",
                "mult": "1..*" or "*..*",
                "quote": "the words in the document that state it",
                "why": "one short sentence"}}]}}

An empty list is the right answer when nothing in the document needs them."""


def _goal_menu(spec):
    """Every goal grouped by its owner, with roots marked.

    The proposal pass has to answer in identifiers the model already contains, or
    nothing it says can be applied without inventing a goal. So it is given the
    identifiers rather than asked to describe what it means.
    """
    label = {a["type"]: (a.get("label") or a["type"]) for a in spec.get("actors", [])}
    by_owner = {}
    for g in spec.get("goals", []):
        by_owner.setdefault(g["owner"], []).append(g)
    lines = ["PARTICIPANTS AND THEIR GOALS"]
    for a in spec.get("actors", []):
        lines.append('- %s (%s..%s)' % (label[a["type"]], a["lo"], a["hi"]))
        for g in by_owner.get(a["type"], []):
            lines.append('    %s%s : %s'
                         % (g["name"], "  [root]" if g.get("root") else "",
                            (g.get("label") or g["name"])))
    lines.append("")
    lines.append("DEPENDENCIES ALREADY IN THE MODEL")
    owner = {g["name"]: g["owner"] for g in spec.get("goals", [])}
    if not spec.get("deps"):
        lines.append("- none")
    for d in spec.get("deps", []):
        lines.append('- %s -> %s (%s), %s needs %s'
                     % (d["from"], d["to"], d.get("mult"),
                        label.get(owner.get(d["from"]), "?"),
                        label.get(owner.get(d["to"]), "?")))
    return "\n".join(lines)


def _resolve_goal(spec, name):
    """Find a goal by name, tolerating the case the proposal came back in.

    Two readings of one document named the same goal `mm_root` and `MM_Root`, so
    an exact match would throw away a correct proposal over its spelling.
    """
    if not name:
        return None
    names = {g["name"] for g in spec.get("goals", [])}
    if name in names:
        return name
    low = {g["name"].lower(): g["name"] for g in spec.get("goals", [])}
    return low.get(str(name).lower())


def verify_dep_recall(spec, trace, text, backend="auto", model=None):
    """Propose dependencies the extraction missed, then confirm each one.

    Two passes on purpose. The proposal pass is told to look hard, which is what
    finds the edge that carries the defect, and a pass told to look hard also
    reaches. The confirming pass never sees that instruction and judges what it is
    handed against the document.
    """
    actors = spec.get("actors", [])
    if len(actors) < 2:
        return {"proposed": [], "results": [], "checked": 0}

    out = _ask(DR_SYSTEM + DR_USER.format(text=text, model=_goal_menu(spec)),
               backend, model)
    if not isinstance(out, dict):
        raise ExtractionError("The dependency recall audit returned nothing usable.")
    raw = list(out.get("missing") or [])

    # And the same question again, asked only about the participants that can be
    # absent, because they are the only ones an edge can turn into a finding.
    absent = [a for a in actors if int(a.get("lo", 0)) == 0]
    if absent:
        by_owner = {}
        for g in spec.get("goals", []):
            by_owner.setdefault(g["owner"], []).append(g)
        lines = []
        for a in absent:
            lines.append('- %s (%s..%s)' % (a.get("label") or a["type"], a["lo"], a["hi"]))
            for g in by_owner.get(a["type"], []):
                lines.append('    %s%s : %s'
                             % (g["name"], "  [root]" if g.get("root") else "",
                                (g.get("label") or g["name"])))
        try:
            out2 = _ask(DA_SYSTEM + DA_USER.format(text=text,
                                                   absent="\n".join(lines),
                                                   model=_goal_menu(spec)), backend, model)
            if isinstance(out2, dict):
                raw += list(out2.get("missing") or [])
        except ExtractionError:
            pass          # the sweep above already produced proposals, so this is
                          # an improvement on the answer and never a gate on it

    owner = {g["name"]: g["owner"] for g in spec.get("goals", [])}
    have = {(d["from"], d["to"]) for d in spec.get("deps", [])}
    proposed, seen, dropped = [], set(), []
    for p in raw:
        if not isinstance(p, dict):
            continue
        f = _resolve_goal(spec, p.get("from"))
        t = _resolve_goal(spec, p.get("to"))
        if not f or not t:
            dropped.append((p.get("from"), p.get("to"),
                            "names a goal the model does not have"))
            continue
        if owner.get(f) == owner.get(t):
            dropped.append((f, t, "both goals belong to the same participant"))
            continue
        if (f, t) in have:
            dropped.append((f, t, "already in the model"))
            continue
        if (f, t) in seen:
            continue
        seen.add((f, t))
        proposed.append({"from": f, "to": t,
                         "mult": p.get("mult") if p.get("mult") in ("1..*", "*..*") else "1..*",
                         "quote": (p.get("quote") or "")[:500],
                         "why": p.get("why") or ""})

    # A cap, said out loud. A proposal pass that reaches could otherwise double the
    # size of the graph, and a silent truncation reads afterwards like a model that
    # had nothing more to say.
    over = []
    if len(proposed) > MAX_PROPOSALS:
        over = proposed[MAX_PROPOSALS:]
        proposed = proposed[:MAX_PROPOSALS]

    if not proposed:
        return {"proposed": [], "results": [], "checked": 0,
                "discarded": dropped, "over_cap": over}

    label = {a["type"]: (a.get("label") or a["type"]) for a in actors}
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec.get("goals", [])}
    lines = []
    for p in proposed:
        key = p["from"] + " -> " + p["to"]
        lines.append(
            '- id: %s\n'
            '  claim: %s cannot achieve "%s" without %s doing "%s"\n'
            '  multiplicity: %s\n'
            '  quoted in support: "%s"'
            % (key, label.get(owner.get(p["from"]), "?"), glabel.get(p["from"], p["from"]),
               label.get(owner.get(p["to"]), "?"), glabel.get(p["to"], p["to"]),
               p["mult"], p["quote"]))

    conf = _ask(DC_SYSTEM + DC_USER.format(text=text, claims="\n".join(lines)),
                backend, model)
    if not isinstance(conf, dict) or "results" not in conf:
        raise ExtractionError("The dependency confirmation returned nothing usable.")
    known = {p["from"] + " -> " + p["to"] for p in proposed}
    results = [r for r in conf["results"]
               if isinstance(r, dict) and r.get("id") in known]
    return {"proposed": proposed, "results": results, "checked": len(proposed),
            "discarded": dropped, "over_cap": over}


def apply_dep_recall_verdicts(spec, trace, audit):
    """Add the confirmed edges. Returns (spec, trace, added, rejected).

    An added edge is marked `added` and its supporting quote is written into the
    trace under the same key an extracted edge would use, so every pass downstream,
    the structure audit, the gap report and the reader, sees it the same way and
    can tell where it came from.
    """
    proposals = {p["from"] + " -> " + p["to"]: p for p in audit.get("proposed", [])}
    out = json.loads(json.dumps(spec))
    tr = json.loads(json.dumps(trace or {}))
    tr.setdefault("deps", {})
    have = {(d["from"], d["to"]) for d in out.get("deps", [])}
    added, rejected = [], []
    for r in audit.get("results", []):
        p = proposals.get(r.get("id"))
        if not p:
            continue
        verdict = r.get("verdict")
        if verdict not in ("supported", "wrong_mult"):
            rejected.append((r["id"], r.get("why") or ""))
            continue
        mult = p["mult"]
        if verdict == "wrong_mult" and r.get("correct_mult") in ("1..*", "*..*"):
            mult = r["correct_mult"]
        quote = (r.get("quote") or p.get("quote") or "").strip()
        if not quote:
            # An edge nobody can check is exactly what this audit exists to avoid
            # producing, so it is refused rather than added unsourced.
            rejected.append((r["id"], "confirmed without a quote, so it was not added"))
            continue
        if (p["from"], p["to"]) in have:
            continue
        out.setdefault("deps", []).append(
            {"from": p["from"], "to": p["to"], "mult": mult,
             "demand": None, "added": True})
        have.add((p["from"], p["to"]))
        tr["deps"][r["id"]] = quote
        added.append((r["id"], mult, quote, p.get("why") or ""))
    return out, tr, added, rejected

if __name__ == "__main__":
    sys.exit(main(sys.argv))
