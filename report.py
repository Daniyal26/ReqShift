"""Turns a GoalShift result into a Markdown report, and into the plain-text digest
that the optional write-up step is allowed to reword.

No language model is involved in this file. Everything printed here is either copied
from the requirements or computed by the solver.
"""

SYM = {"OK": "yes", "X": "no", "-": "absent"}

# How each unconfirmed input reads in a sentence, so the reader knows which of the
# three it is without being handed the internal name.
WHY = {"unsupported": "an unsupported dependency",
       "added": "a dependency an audit added",
       "assumed-absent": "an assumed absence",
       "uncorroborated": "an edge a second reading did not draw",
       "added-then-rejected": "a dependency one audit added and another rejected",
       "unsupported-breakdown": "an unsupported breakdown",
       "unsupported-root": "an unsettled overall goal",
       "wrong-root": "a questioned overall goal"}


def _pattern(pattern):
    return ", ".join(SYM.get(p, p) for p in pattern)


def digest(spec, result, found, trace):
    """The compact, factual brief handed to the write-up step.

    Deliberately terse and complete. It carries the proved results and the requirement
    sentences behind them, so the language model has no reason to reach for anything it
    was not given.
    """
    if not result.get("ok"):
        return "The model did not validate:\n" + "\n".join(result.get("errors", []))

    label = {a["type"]: a.get("label") or a["type"] for a in spec["actors"]}
    order = result["order"]
    lines = ["ACTORS AND CARDINALITIES"]
    for a in spec["actors"]:
        src = trace.get("actors", {}).get(a["type"], "")
        lines.append(f'  {label[a["type"]]}: {a["lo"]} to {a["hi"]} present'
                     + (f'   [source: {src}]' if src else ""))

    lines.append("")
    lines.append("DEPENDENCIES")
    for d in spec["deps"]:
        src = trace.get("deps", {}).get(f'{d["from"]} -> {d["to"]}', "")
        lines.append(f'  {d["from"]} needs {d["to"]} ({d["mult"]})'
                     + (f'   [source: {src}]' if src else ""))

    lines.append("")
    lines.append(f'SOLVER RESULT: {result["stats"]["configurations"]} configurations '
                 f'collapse into {result["stats"]["classes"]} behavior classes.')
    lines.append("Satisfaction pattern is in the order " + ", ".join(label[a] for a in order))
    for c in result["classes"]:
        lines.append(f'  Class {c["class"]}: ({_pattern(c["pattern"])})   '
                     f'{len(c["members"])} configurations, e.g. {c["members"][0]}')

    lines.append("")
    lines.append("FINDINGS")
    if not found:
        lines.append("  None. Every present actor is satisfiable in every configuration.")
    for f in found:
        # The write-up step rewords this brief and may not add to it, so the word
        # PROVED must not appear over a finding that rests on something the
        # document never said. It would be reworded into a claim about the
        # specification rather than about the model.
        # An inert cardinality asserts nothing about the document, so it is neither
        # proved of it nor unconfirmed against it and gets no word.
        state = ("" if f["kind"] == "inert-cardinality"
                 else "[PROVED] " if f.get("proved", True) else "[UNCONFIRMED] ")
        lines.append(f'  {state}[{f["kind"]}] {f["headline"]}')
        if f.get("classes"):
            lines.append(f'      in classes {", ".join(str(c) for c in f["classes"])}, '
                         f'covering {f["configs"]} configurations')
        for c in f.get("causes", []):
            lines.append(f'      cause: "{c["from"]}" depends on "{c["to"]}" from '
                         f'{c["provider"]} ({c["mult"]}), and {c["provider"]} is '
                         f'{c.get("why", "unavailable")} there')
        for r in f.get("rests_on", []):
            lines.append(f'      RESTS ON {WHY.get(r["why"], "an unstated input")}: '
                         f'{r["what"]}')
            lines.append(f'          {r["note"]}')
            if r.get("quote"):
                lines.append(f'          the only sentence behind it: "{r["quote"]}"')
            lines.append('          The solver proved this of the model. Say that the '
                         'model assumes it, never that the document states it.')
        if f.get("unmet"):
            lines.append(f'      unsatisfied at minimum: {", ".join(f["unmet"])} '
                         f'(configuration {f.get("present", "")})')
        if f.get("example"):
            lines.append(f'      example configuration: {f["example"]}')

    if trace.get("notes"):
        lines.append("")
        lines.append("EXTRACTION CAVEATS (from the model that read the requirements)")
        for n in trace["notes"]:
            lines.append(f"  {n}")
    return "\n".join(lines)


def markdown(spec, result, found, trace, source_name, writeup=None):
    label = {a["type"]: a.get("label") or a["type"] for a in spec["actors"]}
    L = [f"# Requirements analysis: {source_name}", ""]

    if not result.get("ok"):
        L += ["The extracted model did not pass GoalShift's validation, so nothing was "
              "analysed. Fix these on the canvas and run again.", ""]
        L += [f"- {e}" for e in result.get("errors", [])]
        return "\n".join(L)

    s = result["stats"]
    problems = [f for f in found if f["kind"] != "inert-cardinality"]
    unconfirmed = [f for f in problems if not f.get("proved", True)]

    # The class COUNT used to lead, and it is the wrong number to lead with. It is not
    # monotonic, so a reader cannot tell which direction is better: 1 is the best
    # possible result and 128 is useless to anybody. Two runs can both report 8 classes
    # with 7 of 8 broken in one and 4 of 8 in the other. What an engineer reacts to is
    # how many of the builds their own specification allows cannot work, which is
    # monotonic and concrete. The classes then do the job they are uniquely good at,
    # which is collapsing those builds into the number of scenarios that cover them.
    broken = sum(len(c["members"]) for c in result["classes"] if "X" in c["pattern"])
    total = s["configurations"]
    bad_classes = sum(1 for c in result["classes"] if "X" in c["pattern"])

    L += ["## Summary", ""]
    if broken:
        L += [f'- Of the **{total} builds** this specification allows, '
              f'**{broken} cannot work**. Something is present in them and provably '
              f'unable to do its job.']
    else:
        L += [f'- Of the **{total} builds** this specification allows, **every one '
              f'works**. There is no combination in which something is present and '
              f'unable to do its job.']
    L += [f'- Those {total} builds collapse into **{s["classes"]} distinct '
          f'behaviour{"" if s["classes"] == 1 else "s"}**, so '
          f'{s["classes"]} test scenario{"" if s["classes"] == 1 else "s"} '
          f'cover{"s" if s["classes"] == 1 else ""} all of them'
          + (f', and {bad_classes} of those behaviour'
             f'{"" if s["classes"] == 1 else "s"} '
             f'{"contains" if bad_classes == 1 else "contain"} something that cannot '
             f'do its job' if bad_classes else "")]
    _st = len(result["statechart"]["states"])
    L += [f'- Behavioral model: {_st} state{"" if _st == 1 else "s"}, '
          f'{len(result["statechart"]["edges"])} join/leave transitions',
          f'- Encoding: {s["variables"]} Boolean variables, {s["clauses"]} CNF clauses, '
          f'{s.get("sat_calls", "?")} SAT checks',
          f'- **{len(problems)} problem{"" if len(problems) == 1 else "s"} found**'
          + (f', **{len(unconfirmed)} of them resting on something the document '
             f'does not state**' if unconfirmed else ""), ""]

    # A clean result is an ANSWER, not an absence, and it did not read like one. On the
    # worked example the tight revision returns one behaviour, no findings and no gaps,
    # which looked like the tool had failed to find anything when it is in fact the
    # outcome the whole exercise is aiming at.
    if not problems and not broken:
        L += ["> **This is the result you want, not an empty one.** Every build this "
              "specification permits behaves the same way, and every participant that "
              "can be present can meet its goal in all of them. That is what a "
              "specification looks like when it has said enough about its own "
              "composition for the question to have a single answer.", ""]

    L += ["Every statement below was proved by the solver from the model. The language "
          "model only read the requirements and proposed that model. It did not decide "
          "any of this.", ""]

    if unconfirmed:
        # The distinction the whole report turns on. A finding can be sound about
        # the model and still be wrong about the specification, and it is wrong in
        # the direction that sells, which is the direction nobody checks.
        count = ("Every finding below rests" if len(unconfirmed) == len(problems)
                 else f'{len(unconfirmed)} of the {len(problems)} findings below '
                      f'{"rests" if len(unconfirmed) == 1 else "rest"}')
        L += ["> **Read the marked findings before acting on them.** "
              f'{count} on something the model asserts and the document does not. '
              "It may be a dependency, a breakdown inside a participant, which goal "
              "that participant is judged against, or whether it may be absent at "
              "all. The solver result is correct for the model as drawn. Whether the "
              "model is right about the specification is the part still open, and "
              "each one carries the sentence you need to settle it.", ""]

    if writeup:
        # Demote the write-up's own headings, whatever level it chose, so they nest under
        # this section instead of competing with the report's structure.
        top = min((len(ln) - len(ln.lstrip("#"))
                   for ln in writeup.splitlines()
                   if ln.startswith("#") and ln.lstrip("#").startswith(" ")), default=3)
        shift = max(0, 3 - top)
        body = "\n".join(("#" * shift + ln) if ln.startswith("#") else ln
                         for ln in writeup.splitlines())
        L += ["## What this means", "",
              "_Written by AI from the findings below. It rewords them and "
              "may not add to them._", "", body, ""]

    L += ["## Findings", ""]
    if not problems:
        L += ["No problems. Every actor that can be present can also meet its goal.", ""]
    for i, f in enumerate(problems, 1):
        mark = "" if f.get("proved", True) else " _(unconfirmed)_"
        L += [f'### {i}. {f["headline"]}{mark}', ""]
        if f["kind"] == "blocked":
            cls = ", ".join(str(c) for c in f["classes"])
            L += [f'{label[f["actor"]]} is present and provably cannot meet its root '
                  f'goal in behavior class{"" if len(f["classes"]) == 1 else "es"} {cls}, '
                  f'covering {f["configs"]} of the {s["configurations"]} configurations. '
                  f'For example `{f["example"]}`.', ""]
        elif f["kind"] == "initial-degraded":
            L += [f'The system starts as `{f["present"]}`, its minimum configuration. '
                  f'In that state {", ".join(f["unmet"])} is present but unsatisfied.', ""]
        elif f["kind"] == "capacity-limit":
            L += [f'The requirements allow up to {f["declared_max"]} of them, but '
                  f'{f["provider"]} capacity only supports **{f["ceiling"]}**. Each one '
                  f'consumes {f["demand"]} and each {f["provider"]} supplies '
                  f'{f["capacity"]}, through "{f["goal"]}" needing "{f["provides"]}".', "",
                  f'The declared upper bound is not the real one. Either raise capacity, '
                  f'or lower the bound to {f["ceiling"]} so the specification stops '
                  f'promising something it cannot deliver.', ""]
        elif f["kind"] == "deadline-miss":
            L += [f'The stated limit is {f["deadline"]:g} and the soonest this can '
                  f'finish is **{f["soonest"]:g}**, a shortfall of '
                  f'{f["shortfall"]:g}. This is the best case, with every choice made '
                  f'favourably and nothing waiting on anything avoidable.', ""]
        elif f["kind"] == "deadline-unreachable":
            L += [f'Its root goal cannot be satisfied in any configuration, so the '
                  f'{f["deadline"]:g} deadline is unreachable for a reason that has '
                  f'nothing to do with timing.', ""]
        elif f["kind"] == "never-satisfied":
            L += [f'{label[f["actor"]]} does not reach its root goal in any of the '
                  f'{s["configurations"]} configurations. Either a dependency cannot be '
                  f'met, or the requirement is unachievable as written.', ""]
        for c in f.get("causes", []):
            tail = ('and the requirements permit zero of them'
                    if c.get("why") == "absent"
                    else 'and it is itself unsatisfied there, so the failure cascades')
            L += [f'- Cause: "{c["from"]}" depends on "{c["to"]}" provided by '
                  f'{c["provider"]} with multiplicity `{c["mult"]}`, {tail}.']
        if f.get("causes"):
            L += [""]
        # The flag, beside the claim it produced rather than in a list elsewhere.
        for r in f.get("rests_on", []):
            L += [f'**This rests on something the document does not state '
                  f'({WHY[r["why"]]}):** `{r["what"]}`', "",
                  f'{r["note"]}', ""]
            if r.get("quote"):
                L += [f'> {_esc(r["quote"])}', ""]
        if f.get("rests_on"):
            L += ['The solver proved this of the model as drawn. Check the sentence '
                  'above before treating it as a defect in the specification.', ""]

    inert = [f for f in found if f["kind"] == "inert-cardinality"]
    if inert:
        L += ["### Worth a look", ""]
        for f in inert:
            L += [f'- {f["headline"]}. The range is allowed by the requirements but does '
                  f'not change any outcome in the model.']
        L += [""]

    L += ["## Behavior classes", "",
          "| Class | " + " | ".join(label[a] for a in result["order"])
          + " | Configurations | Example |",
          "|" + "---|" * (len(result["order"]) + 3)]
    for c in result["classes"]:
        L.append(f'| {c["class"]} | '
                 + " | ".join(SYM.get(p, p) for p in c["pattern"])
                 + f' | {len(c["members"])} | `{c["members"][0]}` |')
    L += ["",
          "These are equivalence classes. Every configuration inside one behaves "
          f'identically, so {s["classes"]} test scenarios cover all '
          f'{s["configurations"]} configurations.', ""]

    L += ["## Behavioral model", "",
          "How the system moves between classes as actors join and leave.", "",
          "```mermaid", "stateDiagram-v2"]
    init = result["statechart"]["initial"]
    if init is not None:
        L.append(f"    [*] --> C{init}")
    for src, lbl, dst in result["statechart"]["edges"]:
        L.append(f"    C{src} --> C{dst}: {lbl}")
    L += ["```", ""]

    L += ["## Traceability", "",
          "Where each part of the model came from in the source text.", "",
          "| Element | Requirement |", "|---|---|"]
    for a in spec["actors"]:
        src = trace.get("actors", {}).get(a["type"], "")
        L.append(f'| Actor {label[a["type"]]} `{a["lo"]}..{a["hi"]}` | {_esc(src)} |')
    for d in spec["deps"]:
        src = trace.get("deps", {}).get(f'{d["from"]} -> {d["to"]}', "")
        # An edge the extraction missed and the recall audit recovered says so here.
        # It supports findings exactly like an extracted one, so the reader is told
        # which pass drew it and can weigh the quote accordingly.
        mark = " (recovered by the dependency audit)" if d.get("added") else ""
        L.append(f'| Dependency {d["from"]} to {d["to"]} `{d["mult"]}`{mark} '
                 f'| {_esc(src)} |')
    L += [""]

    recovered = [d for d in spec["deps"] if d.get("added")]
    if recovered:
        L += ["### Dependencies the extraction missed", "",
              "The extraction did not draw these. A second pass proposed them from the "
              "document and a third confirmed each one against it, and only edges with "
              "a supporting quote were added. They are in the analysis, so a finding "
              "may rest on one. Check the quote in the table above before acting on "
              "such a finding.", ""]
        for d in recovered:
            L.append(f'- `{d["from"]}` needs `{d["to"]}` ({d["mult"]})')
        L += [""]

    if trace.get("notes"):
        L += ["## Extraction caveats", "",
              "Raised by the model that read the requirements. These are its own "
              "uncertainties about the extraction, not solver results.", ""]
        L += [f"- {n}" for n in trace["notes"]]
        L += [""]

    L += ["---", "",
          "Model drafted by AI, analysed by GoalShift. "
          "The extraction is a draft for review. The analysis is proved of that draft, "
          + ("and every finding above rests only on what the document states."
             if not unconfirmed else
             f'and {len(unconfirmed)} finding'
             f'{"" if len(unconfirmed) == 1 else "s"} above also rest on something it '
             f'does not.')]
    return "\n".join(L)


def _esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")
