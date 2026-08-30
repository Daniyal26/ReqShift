"""The only part of ReqShift that talks to a language model.

It does exactly one job: read requirements prose and propose a goal model. It never
judges whether that model is satisfiable, never decides which configurations work, and
never writes a finding. Those come from GoalShift's solver, downstream and unaided.

Two backends, same schema:

  sdk  - the official Anthropic SDK with structured outputs. Needs a credential.
  cli  - the `claude` command from Claude Code. Needs no key if you are already
         signed in there, which makes it the zero-setup path.
"""
import json
import os
import shutil
import subprocess

from schema import EXTRACTION_SCHEMA, OPS, MULTS

MODEL = "claude-opus-5"

SYSTEM = """You extract goal models from engineering requirements.

You are the front half of a formal verification tool. A SAT solver downstream will
decide which system configurations satisfy their goals. Your job is only to turn prose
into a structured model for it to reason over. Never state or imply a conclusion about
whether something is satisfiable, achievable, or correct. That is not your call.

The target notation is iStar-style, restricted:

ACTORS are kinds of participant, never individuals. "Up to four welding robots" is one
actor type with hi=4, not four actors. Give every actor a cardinality range. lo is 0 if
the system can run without it and 1 if at least one must always be present. Only 0 and 1
are supported for lo. hi is the maximum that can be present at once.

An actor must be something whose PRESENCE OR ABSENCE decides whether the system can do
its job. Apply that test literally and exclude anything that fails it:

- NOT human roles or user classes. Operators, administrators, astronomers, engineers,
  technicians, web users and the like use the system. Their headcount does not decide
  whether it works. Model them only when the text says the system cannot function
  without a stated number of them present.
- NOT documents, data, records, messages, files or reports. Those are things the system
  handles, not participants that can be missing.
- NOT the system as a whole, and not a subsystem that is always present exactly once
  unless something genuinely depends on its absence.

hi IS ONLY FOR A NUMBER THE TEXT ACTUALLY STATES. This matters more than anything else
here. If the document does not say how many, set "hi_stated": false and put your best
reading in hi anyway, but never invent a large number to mean "many". Phrases like "one
or more", "multiple", "a few", "all of them" and "the remaining ones" state NO maximum.
Numbers that measure something else are not counts of the actor either: road miles,
gigabytes per second, concurrent users, transactions per year, and numbers of types or
categories are all traps. When in doubt, hi_stated is false.

GOALS belong to exactly one actor. Each actor has exactly one root goal, the thing that
actor is ultimately there to achieve.

DECOMPOSITION breaks a goal into sub-goals of the SAME actor. AND means every child is
needed. OR means at least one child. XOR means exactly one of exactly two children, so
never give XOR more or fewer than two children.

DEPENDENCIES are the only link allowed between different actors. A dependency says a
goal of actor A can only be met with help from a goal of actor B. Multiplicity 1..* means
at least one present provider must supply it. *..* means every present provider must.

Rules you must not break:
- Never connect two actors with a decomposition. Cross-actor means dependency.
- Every name is a short identifier without spaces. Put the readable wording in label.
- Extract cardinalities wherever the text implies them. Numbers buried in prose like
  "up to six" or "at least one" are the most valuable thing you produce.
- Quote the source sentence verbatim for every element. If something is implied rather
  than written, say so in the source field and explain briefly.
- Do not invent dependencies to make the model look connected. If the text does not say
  one thing needs another, do not link them.
- Put everything you were unsure about in notes. An honest note is worth more than a
  confident guess, because a human reviews this model before it is analysed.

NUMBERS. Four optional numeric fields exist, and they matter because they are the only
way anything beyond plain yes/no reasoning becomes possible. Fill them ONLY when the
text actually gives the figure, and leave them null otherwise. Never estimate one.

- duration on a goal: how long it takes once its prerequisites are met. "the weld
  program takes 45 seconds" gives duration 45. Pick ONE time unit for the whole model,
  convert everything into it, and say which unit you used in notes.
- deadline on an actor: a limit on its root goal. "the ambulance shall reach the scene
  within 8 minutes" is a deadline on the ambulance, in the same unit as the durations.
- capacity on an actor: how many units ONE instance can serve. "each hospital has 12
  beds" gives capacity 12.
- demand on a dependency: how many units EACH depending instance consumes. "each
  ambulance brings one patient" gives demand 1 on the ambulance-to-hospital dependency.

capacity and demand only do anything as a pair, so if the text gives one and not the
other, set the one you have and say in notes that its partner is missing."""

USER_TEMPLATE = """Extract the goal model from these requirements.

<requirements>
{text}
</requirements>

Return the model. Remember that a human will review it on a canvas before anything is
analysed, so flag your uncertainties in notes rather than smoothing them over."""


class ExtractionError(RuntimeError):
    pass


def available_backends():
    """Which backends could actually run right now, best first."""
    out = []
    try:
        import anthropic  # noqa: F401
        if (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or shutil.which("ant")):
            out.append("sdk")
    except ImportError:
        pass
    if _claude_cli():
        out.append("cli")
    return out


def _claude_cli():
    for name in ("claude", "claude.cmd", "claude.exe"):
        p = shutil.which(name)
        if p:
            return p
    local = os.path.expanduser("~/.local/bin/claude")
    return local if os.path.exists(local) else None


# How long one call may take before it is treated as hung. Extraction on an 83 page
# specification runs several minutes, so this cannot be tight, but 1800s was far too
# loose: on 25 August a single audit call hung and the run sat there for the full half
# hour before failing. Nothing this pipeline asks for legitimately takes ten minutes,
# and an audit that gives up is now survivable, so the wait is worth less than the time.
# Two limits, because the two kinds of call are not alike. Extraction reads the whole
# document and builds a model, and on the 83 page substation specification that alone
# took 456 seconds, so it needs real headroom. An audit answers one narrow question and
# has never legitimately taken minutes. Measuring them the same way is how a hung audit
# was allowed to sit for half an hour.
CALL_TIMEOUT = int(os.environ.get("REQSHIFT_CALL_TIMEOUT", "600"))          # audits
EXTRACT_TIMEOUT = int(os.environ.get("REQSHIFT_EXTRACT_TIMEOUT", "1800"))   # extraction


def _run_cli(exe, prompt, timeout=None):
    """Send a prompt to the `claude` command via stdin.

    stdin rather than argv on purpose. A real requirements document passed as a command
    line argument overflows the Windows 32k limit and fails in a confusing way.
    """
    proc = subprocess.run([exe, "-p"], input=prompt, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          timeout=timeout or CALL_TIMEOUT)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        low = detail.lower()
        if "session limit" in low or "usage limit" in low:
            raise ExtractionError(
                "Claude Code says you have hit your session limit, so the request did "
                "not run.\n" + detail.splitlines()[0]
                + "\nWait for the reset, or use --backend sdk with an API key.")
        raise ExtractionError(f"`claude` exited {proc.returncode}.\n{detail[:2000]}")
    return proc.stdout


def extract(text, backend="auto", model=MODEL):
    """Requirements prose -> the flat dict described by EXTRACTION_SCHEMA."""
    if backend == "auto":
        options = available_backends()
        if not options:
            raise ExtractionError(
                "No way to reach Claude. Either install the SDK and set a credential\n"
                "  pip install anthropic  and  set ANTHROPIC_API_KEY\n"
                "or sign in to Claude Code, which puts a `claude` command on your PATH.")
        backend = options[0]
    if backend == "sdk":
        return _extract_sdk(text, model)
    if backend == "cli":
        return _extract_cli(text, model)
    raise ExtractionError(f"Unknown backend {backend!r}. Use sdk, cli, or auto.")


def _extract_sdk(text, model):
    import anthropic

    client = anthropic.Anthropic()
    # Thinking is adaptive by default on Opus 5, so it is deliberately not set here.
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": USER_TEMPLATE.format(text=text)}],
        output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise ExtractionError(
            "Claude declined this request. Details: "
            f"{getattr(response, 'stop_details', None)}")
    try:
        payload = next(b.text for b in response.content if b.type == "text")
    except StopIteration:
        raise ExtractionError("The response contained no text block.")
    return json.loads(payload)


def _extract_cli(text, model):
    exe = _claude_cli()
    if not exe:
        raise ExtractionError("The `claude` command was not found on your PATH.")

    # The CLI has no structured-output constraint, so the schema goes in the prompt and
    # the reply is parsed defensively.
    prompt = (SYSTEM + "\n\n" + USER_TEMPLATE.format(text=text) + "\n\n"
              "Reply with a single JSON object and nothing else. No prose before or "
              "after it, no markdown fence. It must validate against this JSON schema:\n"
              + json.dumps(EXTRACTION_SCHEMA))

    return _loads_loose(_run_cli(exe, prompt, EXTRACT_TIMEOUT))


def _loads_loose(s):
    """Parse JSON that may be wrapped in a fence or trailed by a stray sentence."""
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    if start == -1:
        raise ExtractionError(f"No JSON object in the reply.\n{s[:800]}")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(s[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                block = s[start:i + 1]
                try:
                    return json.loads(block)
                except json.JSONDecodeError as e:
                    try:
                        return json.loads(_escape_inner_quotes(block))
                    except json.JSONDecodeError:
                        raise ExtractionError(f"The reply was not valid JSON: {e}")
    raise ExtractionError(f"The JSON object in the reply was never closed.\n{s[:800]}")


def _escape_inner_quotes(block):
    """Rescue JSON where a string value quotes something without escaping it.

    Models sometimes write   "reason": "phrases like "up to 120" appear"   which is
    good English and invalid JSON. A quote is taken to close its string only when
    the next non-space character is one that may legitimately follow a string, so
    a comma, a colon, or a closing brace or bracket. Any other quote inside a
    string was meant literally and is escaped instead.
    """
    out, in_str, esc = [], False, False
    for i, ch in enumerate(block):
        if not in_str:
            out.append(ch)
            if ch == '"':
                in_str = True
            continue
        if esc:
            out.append(ch)
            esc = False
            continue
        if ch == "\\":
            out.append(ch)
            esc = True
            continue
        if ch == '"':
            nxt = next((c for c in block[i + 1:] if not c.isspace()), "")
            if nxt in ",:}]" or nxt == "":
                out.append(ch)
                in_str = False
            else:
                out.append('\\"')
            continue
        out.append(ch)
    return "".join(out)


def explain(findings_text, backend="auto", model=MODEL):
    """Turn already-computed findings into prose an engineer can read.

    Every fact in `findings_text` came from the solver. This call only rewords it, and
    the prompt says so, because the whole point is that the language model is never the
    thing that decided something was wrong.
    """
    prompt = (
        "Below are results a SAT solver produced from a goal model, together with the "
        "requirement sentences behind them. Write them up for a systems engineer.\n\n"
        "Every fact here is already proved. Reword it, do not re-derive it, do not "
        "second-guess it, and do not add findings of your own. Where a problem is "
        "reported, name the requirement sentence responsible and say what a person "
        "would have to decide to resolve it. Be brief and concrete. No preamble.\n\n"
        "House style: never use em dashes. Start your headings at level 3 (###), "
        "because this is embedded inside a larger report.\n\n"
        + findings_text)

    if backend == "auto":
        options = available_backends()
        if not options:
            raise ExtractionError("No way to reach Claude for the write-up.")
        backend = options[0]

    if backend == "cli":
        exe = _claude_cli()
        if not exe:
            raise ExtractionError("The `claude` command was not found on your PATH.")
        return _run_cli(exe, prompt).strip()

    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model, max_tokens=16000,
        messages=[{"role": "user", "content": prompt}])
    if getattr(response, "stop_reason", None) == "refusal":
        raise ExtractionError("Claude declined to write up these findings.")
    return "".join(b.text for b in response.content if b.type == "text").strip()
