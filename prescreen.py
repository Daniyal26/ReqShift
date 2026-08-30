"""Cheap scope gate. Ask ONE question before paying for a full extraction.

Experiment A, 22 Aug 2026, found that the extractor never declines. GParted, a
disk partition editor with nothing that varies in number, came back with 15
actor types and 86 trillion configurations. Only one document in ten refused,
and it took 624 seconds to do it.

The whole analysis is only meaningful when a document describes two or more
kinds of thing where at least one varies in number within a STATED bound. That
is a yes/no question, and answering it is far cheaper than building a model.

    py -3 prescreen.py path/to/requirements.txt

Returns in seconds instead of minutes, and rejects work that would be wasted.
"""
import json
import sys

import extractor
from extractor import ExtractionError

SYSTEM = """You decide whether a requirements document is worth analysing with a
configuration solver. You do NOT build a model. You answer one question.

The solver reasons about systems assembled from a VARYING NUMBER of cooperating
parts, and it can only say something useful when all three of these hold:

  1. The document describes TWO OR MORE kinds of participant, not just one system
     with functions.
  2. At least one of those kinds can be present in DIFFERENT NUMBERS, or be absent
     entirely, while the system still runs.
  3. The document STATES a bound for that number. "Up to four welding robots" and
     "between two and six cells" qualify. "Multiple users", "many sensors" and any
     number you would have to invent do NOT.

Rule 3 is the one that matters most and the one people get wrong. A document that
merely implies something can vary, without ever saying how much, fails.

Things that do NOT make a document in scope:
  - human roles and user classes (operators, administrators, astronomers, web users).
    They use the system, their headcount does not decide whether it works.
  - counts of data, records, transactions, files, or messages.
  - quantities that measure something other than the participants themselves, such
    as road miles, floor area, budget, or throughput.
  - one program with many features, however many features it has.

Be strict. Saying no is cheap and correct far more often than people expect. If you
are unsure, answer no and say why in the reason.

House style: never use em dashes or en dashes. Use a comma or a full stop instead."""

USER = """Decide whether this document is in scope.

<document>
{text}
</document>

Answer with JSON only, no preamble:

{{"in_scope": true or false,
  "reason": "one sentence",
  "varying_parts": [{{"what": "name of the kind of thing",
                      "stated_bound": "the words in the document that give the number",
                      "quote": "the sentence, verbatim"}}],
  "confidence": "high" or "low"}}

`varying_parts` must be empty when in_scope is false. Every entry must carry a real
quote from the document. If you cannot quote a stated bound, the document is not in
scope."""


def prescreen(text, backend="auto", model=extractor.MODEL):
    """Return the scope verdict for one document. Cheap: one short reply."""
    prompt = SYSTEM + "\n\n" + USER.format(text=text)
    if backend == "auto":
        options = extractor.available_backends()
        if not options:
            raise ExtractionError("No way to reach Claude for the pre-screen.")
        backend = options[0]

    if backend == "cli":
        exe = extractor._claude_cli()
        if not exe:
            raise ExtractionError("The `claude` command was not found on your PATH.")
        raw = extractor._run_cli(exe, prompt)
    else:
        import anthropic
        client = anthropic.Anthropic()
        r = client.messages.create(model=model, max_tokens=2000,
                                   messages=[{"role": "user", "content": prompt}])
        raw = "".join(b.text for b in r.content if b.type == "text")

    v = extractor._loads_loose(raw)
    if not isinstance(v, dict) or "in_scope" not in v:
        raise ExtractionError(f"Pre-screen returned no verdict.\n{raw[:400]}")
    v.setdefault("varying_parts", [])
    v.setdefault("reason", "")
    v.setdefault("confidence", "low")
    if not v["in_scope"]:
        v["varying_parts"] = []
    return v


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    text = sys.stdin.read() if argv[1] == "-" else open(
        argv[1], encoding="utf-8", errors="replace").read()
    v = prescreen(text)
    print(json.dumps(v, indent=1))
    if v["in_scope"]:
        print(f"\nIN SCOPE ({v['confidence']} confidence). {v['reason']}")
        for p in v["varying_parts"]:
            print(f"  - {p.get('what')}: {p.get('stated_bound')}")
        return 0
    print(f"\nNOT IN SCOPE. {v['reason']}")
    print("Extraction would waste several minutes and produce a model nothing can analyse.")
    return 4


if __name__ == "__main__":
    sys.exit(main(sys.argv))
