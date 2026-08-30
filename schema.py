"""The contract between the language model and GoalShift.

One JSON schema, used twice. The Anthropic SDK backend passes it to the API as a
structured-output constraint, and the Claude CLI backend embeds it in the prompt.
Defining it once is what keeps the two backends honest with each other.

The model emits a FLAT shape (every field is a list) rather than GoalShift's spec
directly, because GoalShift's `roots` is a map keyed by actor name and dynamic keys
cannot be constrained by a JSON schema. `to_spec` does the small conversion.

Nothing in here decides anything about satisfaction. This file only describes the
shape of a goal model. Whether the model is satisfiable is GoalShift's business.
"""

# Values the GoalShift engine accepts. Keep these in step with engine.Model.validate.
OPS = ["AND", "OR", "XOR"]
MULTS = ["1..*", "*..*"]
KINDS = ["goal", "task"]

_SOURCE = {
    "type": "string",
    "description": "The sentence from the requirements this came from, quoted verbatim. "
                   "If it is implied rather than stated, write 'implied: <why>'.",
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "actors": {
            "type": "array",
            "description": "One entry per KIND of participant, not per individual. "
                           "'up to four welding robots' is ONE actor type with hi=4.",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string",
                             "description": "Short identifier, no spaces, e.g. Robot"},
                    "label": {"type": "string",
                              "description": "Human-readable name, e.g. Welding Robot"},
                    "lo": {"type": "integer", "minimum": 0,
                           "description": "The fewest that can be present at once. 0 if this "
                                          "actor can be absent, 1 if at least one is always "
                                          "present. Use a HIGHER number only when the document "
                                          "states one, as in 'at least three robots shall be "
                                          "present'. Do not invent a minimum: 1 is the right "
                                          "answer for 'a robot is present', 3 only for 'at "
                                          "least three'."},
                    "hi": {"type": "integer", "minimum": 1,
                           "description": "Maximum number that can be present at once."},
                    "hi_stated": {"type": "boolean",
                                  "description": "True ONLY when the document states this "
                                                 "maximum as a number of these actors. False "
                                                 "when hi is your reading rather than the "
                                                 "document's word. 'one or more', 'multiple', "
                                                 "'a few' state no maximum. Numbers measuring "
                                                 "something else (road miles, concurrent "
                                                 "users, types of a thing) are not counts of "
                                                 "the actor."},
                    "root": {"type": "string",
                             "description": "Name of this actor's top-level goal. Must appear "
                                            "in goals with this actor as owner."},
                    "capacity": {"type": ["integer", "null"], "minimum": 1,
                                 "description": "How many units ONE instance can serve, if "
                                                "the text states it (e.g. 'each hospital has "
                                                "12 beds'). Null when not stated."},
                    "deadline": {"type": ["number", "null"], "minimum": 0,
                                 "description": "Time limit for this actor's root goal, in the "
                                                "same unit as durations, if the text states "
                                                "one. Null when not stated."},
                    "source": _SOURCE,
                },
                "required": ["type", "label", "lo", "hi", "hi_stated", "root",
                             "capacity", "deadline", "source"],
                "additionalProperties": False,
            },
        },
        "goals": {
            "type": "array",
            "description": "Every goal and task, including the roots.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string",
                             "description": "Short unique identifier, no spaces."},
                    "label": {"type": "string", "description": "Human-readable wording."},
                    "owner": {"type": "string",
                              "description": "The actor type this belongs to."},
                    "kind": {"type": "string", "enum": KINDS,
                             "description": "'task' for a concrete operation, else 'goal'."},
                    "duration": {"type": ["number", "null"], "minimum": 0,
                                 "description": "How long this takes once its prerequisites "
                                                "are met, if the text gives a figure. Use one "
                                                "consistent unit across the whole model and "
                                                "say which in notes. Null when not stated."},
                    "source": _SOURCE,
                },
                "required": ["name", "label", "owner", "kind", "duration", "source"],
                "additionalProperties": False,
            },
        },
        "decomp": {
            "type": "array",
            "description": "How a goal breaks into sub-goals. Parent and children must belong "
                           "to the SAME actor. Use a dependency for anything crossing actors.",
            "items": {
                "type": "object",
                "properties": {
                    "parent": {"type": "string"},
                    "op": {"type": "string", "enum": OPS,
                           "description": "AND = every child needed. OR = at least one child. "
                                          "XOR = exactly one of exactly two children."},
                    "children": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "source": _SOURCE,
                },
                "required": ["parent", "op", "children", "source"],
                "additionalProperties": False,
            },
        },
        "deps": {
            "type": "array",
            "description": "A goal of one actor that can only be met with help from another "
                           "actor. This is the ONLY way actors may be connected.",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string",
                             "description": "The depending goal, the one needing help."},
                    "to": {"type": "string",
                           "description": "The depended-on goal, owned by a different actor."},
                    "mult": {"type": "string", "enum": MULTS,
                             "description": "'1..*' = at least one provider must supply it. "
                                            "'*..*' = every present provider must supply it."},
                    "demand": {"type": ["integer", "null"], "minimum": 1,
                               "description": "How many units EACH depending instance consumes "
                                              "from the provider, if the text states it (e.g. "
                                              "'each ambulance brings one patient'). Pairs "
                                              "with the provider's capacity. Null if not stated."},
                    "source": _SOURCE,
                },
                "required": ["from", "to", "mult", "demand", "source"],
                "additionalProperties": False,
            },
        },
        "notes": {
            "type": "array",
            "description": "Anything in the requirements that could not be represented, was "
                           "ambiguous, or had to be assumed. Be candid here.",
            "items": {"type": "string"},
        },
    },
    "required": ["actors", "goals", "decomp", "deps", "notes"],
    "additionalProperties": False,
}


def to_spec(extracted):
    """Flat extraction -> the exact JSON GoalShift's canvas and engine already read.

    Returns (spec, trace). `spec` carries no extra keys, so it can be dropped straight
    into GoalShift. `trace` holds the requirement sentence behind each element.
    """
    roots = {a["type"]: a["root"] for a in extracted["actors"]}
    root_names = set(roots.values())

    def _num(d, key, cast):
        v = d.get(key)
        return {} if v is None else {key: cast(v)}

    spec = {
        "actors": [dict({"type": a["type"], "lo": int(a["lo"]), "hi": int(a["hi"]),
                         "label": a.get("label") or a["type"],
                         # Older extractions predate hi_stated. Absent means unknown,
                         # and unknown must not be mistaken for "the document said so".
                         "hi_stated": bool(a.get("hi_stated", False))},
                        **_num(a, "capacity", int), **_num(a, "deadline", float))
                   for a in extracted["actors"]],
        "roots": roots,
        "goals": [dict({"name": g["name"], "owner": g["owner"],
                        "kind": g.get("kind", "goal"), "root": g["name"] in root_names,
                        "label": g.get("label") or g["name"]},
                       **_num(g, "duration", float))
                  for g in extracted["goals"]],
        "decomp": [{"parent": d["parent"], "op": d["op"], "children": list(d["children"])}
                   for d in extracted["decomp"]],
        "deps": [dict({"from": d["from"], "to": d["to"], "mult": d["mult"]},
                      **_num(d, "demand", int))
                 for d in extracted["deps"]],
    }

    trace = {"actors": {a["type"]: a.get("source", "") for a in extracted["actors"]},
             "goals": {g["name"]: g.get("source", "") for g in extracted["goals"]},
             "decomp": {d["parent"]: d.get("source", "") for d in extracted["decomp"]},
             "deps": {f'{d["from"]} -> {d["to"]}': d.get("source", "")
                      for d in extracted["deps"]},
             "notes": list(extracted.get("notes", []))}
    return spec, trace


def shape_errors(extracted):
    """Problems detectable without the solver, phrased for whoever has to fix them.

    GoalShift's own validator catches the modelling errors. This only catches the ones
    that would crash the conversion before the validator ever runs.
    """
    errs = []
    actors = {a["type"] for a in extracted.get("actors", [])}
    goals = {g["name"] for g in extracted.get("goals", [])}

    if not actors:
        errs.append("No actor types were extracted. The text may not describe a "
                    "multi-actor system, or it may be too short.")

    seen = set()
    for g in extracted.get("goals", []):
        if g["name"] in seen:
            errs.append(f'Duplicate goal name "{g["name"]}". Names must be unique.')
        seen.add(g["name"])
        if g["owner"] not in actors:
            errs.append(f'Goal "{g["name"]}" is owned by "{g["owner"]}", which is not '
                        f'an extracted actor type.')

    for a in extracted.get("actors", []):
        if a["root"] not in goals:
            errs.append(f'Actor {a["type"]} names root goal "{a["root"]}", which is not '
                        f'in the goal list.')

    for d in extracted.get("decomp", []):
        for n in [d["parent"]] + list(d["children"]):
            if n not in goals:
                errs.append(f'Decomposition of "{d["parent"]}" refers to "{n}", '
                            f'which is not a known goal.')
        if d["op"] == "XOR" and len(d["children"]) != 2:
            errs.append(f'XOR decomposition of "{d["parent"]}" has {len(d["children"])} '
                        f'children. The engine requires exactly 2.')

    for d in extracted.get("deps", []):
        for n in (d["from"], d["to"]):
            if n not in goals:
                errs.append(f'Dependency {d["from"]} -> {d["to"]} refers to "{n}", '
                            f'which is not a known goal.')
    return errs
