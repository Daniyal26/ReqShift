# ReqShift

Requirements prose in, analysed goal model out.

```
py -3 reqshift.py examples/welding_cell.txt
```

ReqShift is the AI front end for GoalShift. It reads an engineering requirements
document, proposes a goal model, hands that model to GoalShift's solver, and reports
what the solver proved.

**GoalShift itself is not modified and not copied.** It is imported. This project can be
deleted at any time and GoalShift is exactly as it was, which matters because GoalShift
is the artifact the thesis and the paper describe, and the paper contains no AI.

## The point

A language model cannot tell you when it is wrong. A SAT solver cannot read prose.
Their weaknesses are opposites, so each covers the other:

```
requirements document
    |   Claude                  a DRAFT. review it.
goal model
    |   GoalShift + SAT         PROVED. this is the product.
behavior classes, statechart, findings
    |   Claude (optional)       rewording of proved facts only
report
```

Nothing the tool *claims* comes from the language model. The language model produces the
input and, optionally, the prose wrapper. Every finding is derived arithmetically from
the solver's output, in `analyze.py`, which never calls a model at all.

That is the whole design. It is why a finding here cannot be hallucinated.

## The web UI

```
py -3 app.py                 then open http://localhost:8020
```

Paste requirements, pick an engine, press Analyze, watch the stages, read the result.
The engine dropdown offers **GoalShift (SAT)**, the default, and **z3 (SMT)** when z3 is
installed. Whichever ran is named in a banner at the top of the result, and the SMT one
carries the caveat that it is not proved by the thesis encoding. It shows the
findings, a colored grid of every configuration, the behavior classes, the extracted goal
model, the statechart, and the traceability table. Light and dark. Buttons at the bottom
open the model on the GoalShift canvas, which travels in the URL hash and falls back to the
clipboard when it is too big for one, download the model or the report, or save a run to
`out_ui/`.

### The two steps

The result page is deliberately in two steps, because the numbers this analysis needs are
usually not in the document. Across 31 public engineering documents, not one stated how
many units of a component the system may have.

**Step 1** is the gap report. It runs on any document and lists the quantities that one
never states, ranked by whether their absence can actually break something. Anything the
solver could still prove is shown underneath, marked *provisional*, because every unstated
bound was filled with a placeholder and the configuration count is therefore not the
reader's real one.

**Step 2** is the same analysis re-proved after the reader types those numbers in. It posts
to `/api/reanalyze`, which runs the solver on the edited model with no language model
involved, so it answers in milliseconds rather than minutes. Nothing is invented at any
point: the numbers come from the only party who has them.

Two limits are enforced on what can be typed, both measured rather than guessed. **No actor
may exceed 20 instances**, because GoalShift reasons about every instance separately and
the clause count roughly quadruples for every two more (18 instances is 1.0M clauses and
4.6s, 20 is 4.2M and 14s, 22 is 16.8M and 70s). The whole model may not exceed 20,000
configurations. Past either, the answer is a refusal that names the actor responsible and
points at z3, which counts instead of enumerating.

`examples/bottling_line.txt` and `examples/bottling_line_fixed.txt` are the same document
either side of that fix, so running both shows what step 2 is for.

**Why it needs a server at all.** GoalShift is a single file you double-click because
everything it does runs in the browser. ReqShift has to call Claude, which needs a
credential, and a credential cannot live in a file you hand to someone else. Browsers
also block a `file://` page from calling an outside API. That is the only reason the
architectures differ.

`viewer.py` is separate and much smaller: it just renders `report.md` files that runs
have already produced, with no ability to analyse anything.

## Install

```
pip install python-sat        # GoalShift's solver, required
pip install pdfplumber        # PDF input, required to read a PDF
pip install anthropic         # only for the sdk backend
```

You need one way to reach Claude:

- **cli** (no API key) uses the `claude` command from Claude Code. If you are signed in
  there, this works with no further setup. This is the default when no key is present.
- **sdk** uses the official Anthropic SDK with structured outputs, which constrains the
  reply to the schema at the API level rather than by asking nicely. Needs
  `ANTHROPIC_API_KEY`, or an `ant auth login` profile.

Pick one with `--backend cli` or `--backend sdk`. The default, `auto`, prefers the SDK
when a credential exists and falls back to the CLI.

## Use

```
py -3 reqshift.py path/to/requirements.pdf          # a PDF, or .txt or .md
py -3 reqshift.py requirements.txt --explain        # also write the findings up in prose
py -3 reqshift.py --spec out/model.spec.json        # re-analyse a model, no LLM call
cat spec.md | py -3 reqshift.py -                   # from stdin
```

Useful flags: `-o` output directory, `--backend`, `--model`, `--goalshift <dir>` if the
GoalModelTool folder is not the sibling of this one.

### What lands in the output folder

| File | What it is |
|---|---|
| `report.md` | the readable result, findings first |
| `model.spec.json` | the goal model in GoalShift's own format |
| `model.trace.json` | which requirement sentence each element came from |
| `findings.txt` | what the solver found as plain text, each one marked proved or unconfirmed, and the brief `--explain` is given |
| `analysis.json` | everything, machine readable |
| `open_in_goalshift.txt` | one line to paste to see the model on the canvas |

### Reviewing the model on the canvas

The extraction is a draft, so look at it before trusting its shape. Open
`GoalModelTool/index.html`, press F12 for the console, and paste the line from
`open_in_goalshift.txt`:

```js
loadFromSpec({"actors":[...],"roots":{...},...})
```

The model appears on the canvas laid out, and every GoalShift feature works on it
normally. Correct whatever is wrong by dragging, then click Analyze.

The console route is deliberate. GoalShift's Load button reads its own canvas format
with saved coordinates, and teaching it to also accept a bare spec would mean editing
GoalShift. `loadFromSpec` is already there and already does the layout, so nothing needs
to change.

## The SMT backend (experimental)

```
py -3 reqshift.py model.txt --smt
py -3 bench/diff_smt.py            # check it against GoalShift
```

`analyze_smt.py` analyses the same models with z3 integer counts instead of one
Boolean per possible instance. **GoalShift is untouched and stays the default**, but
the default is now decided by the MODEL rather than by a dropdown: `engine_for()`
switches to z3 when the model states a minimum above one, which SAT rejects outright,
or when it states capacity, demand, duration or a deadline, which SAT does not reject
but silently ignores. Whichever engine ran is named in the result, with the reason.
`--smt` still forces it.

**What it lifts.** `lo` may exceed 1, so "at least three robots" becomes expressible.
The SAT encoding rejects that outright.

**What it removes.** The configuration enumeration. Every place a count is read, the
notation only asks whether it is zero:

```
1..*   holds when  n_provider >= 1   and the provider's goal holds
*..*   holds when  n_provider == 0   or  the provider's goal holds
goals are false when  n_actor == 0
```

Nothing can tell two present hospitals from three. So the pattern depends on the
zero/nonzero vector alone, of which there are at most 2^k for k actor types, whatever
the ranges are. That also *explains* the "inert cardinality" finding rather than
merely detecting it.

The classes come back symbolic, which is a better answer than a list:

```
Class 4  (OK, OK, OK)   15 configurations
    holds when   n_D = 1 and 1 <= n_H <= 3 and 1 <= n_M <= 5
```

| max instances per type | configurations | SMT calls |
|---|---|---|
| 3 | 64 | 20 |
| 100 | 1,020,100 | 12 |
| 1,000,000 | 10^18 | 12 |

**The one assumption, stated plainly.** It carries one Boolean per goal per actor
*type*, not per instance, assuming the present instances of a type can be taken to
behave alike when deciding that type's satisfaction. Instances are interchangeable and
share no constraint, so this should be exact on this notation, but it is an assumption,
not a proof. `bench/diff_smt.py` is what makes it trustworthy: **77 models, GoalShift
as the oracle, 0 mismatches**, including the Chapter 7 case study. Run it after any
change to the encoding.

### Timing and capacity

Four optional numeric fields. The extractor fills them only when the text states the
figure, and leaves them out otherwise.

| Field | On | Means |
|---|---|---|
| `duration` | a goal | how long it takes once its prerequisites are met |
| `deadline` | an actor | its root goal must finish within this |
| `capacity` | an actor | how many units ONE instance can serve |
| `demand` | a dependency | how many units EACH depending instance consumes |

`AND` is read as sequential, which is the conservative reading since the notation has
no ordering. Put `"parallel": true` on a decomposition to use the longest child instead
of the sum. Capacity is aggregate, `n_depending * demand <= n_providing * capacity`, so
it says whether the group can cope, not who serves whom.

**Adding either changes the shape of the problem.** Once a real number is in play the
answer stops depending only on whether a count is zero, so the fast region path is
dropped and configurations are walked. That is why `--smt` is slower on a model with
timing than on one without.

Two findings become possible, and both are *solved for* rather than observed, so the
numbers are exact rather than the largest case that happened to be tried:

```
! Treatment Van is capped at 4 by Clinic Site capacity, not by its own bound of 8
! Scheduling Office cannot meet its 60 deadline. The soonest it can finish is 85
```

`examples/dialysis_unit.txt` states its figures in prose. Run it and the capacity
produces a behavior class that cannot exist in the Boolean model at all: vans present,
clinic present, and the vans blocked because there are not enough treatment bays.

**What you give up.** A model analysed this way is no longer proved by the encoding the
thesis describes. Say which engine produced a result whenever you show one.

## What it finds

Four kinds of finding, all computed from the solver's output:

- **blocked** an actor can be present and provably unable to meet its root goal. The
  expensive one, because the equipment is switched on and doing nothing. Reports which
  dependency caused it and whether the provider was absent or itself unsatisfied.
- **never-satisfied** an actor reaches its root goal in no configuration at all. Usually
  an extraction mistake or a genuinely unachievable requirement.
- **initial-degraded** the minimum configuration, the state the system boots into, does
  not satisfy everything present.
- **inert-cardinality** a range the requirements allow that changes no outcome. Worth
  knowing before someone plans capacity around a number that does nothing.

The report also carries the behavior classes as a test matrix. They are equivalence
classes, so *n* scenarios cover every configuration, and that reduction is proved rather
than asserted.

## Files

| File | Role |
|---|---|
| `intake.py` | turns a PDF into text whose sentences still match the document |
| `schema.py` | the JSON schema Claude must fill in, plus conversion to GoalShift's spec |
| `extractor.py` | the only file that talks to a model. Two backends, one schema |
| `prescreen.py` | the scope gate. Ten seconds, before paying for an extraction |
| `verify.py` | audits every extracted bound against its own citation, as a separate call |
| `gaps.py` | the step 1 report: quantities the document never states, ranked structurally, plus capacity, demand and timing numbers whose other half is missing |
| `analyze.py` | imports GoalShift, derives findings. No model involved |
| `analyze_smt.py` | the experimental z3 backend, integer cardinalities. Opt-in |
| `bench/diff_smt.py` | SAT vs SMT differential test, GoalShift as the oracle |
| `bench/pdf_roundtrip.py` | prints a spec to a hostile PDF and checks the sentences survive |
| `report.py` | Markdown report and the plain-text brief. No model involved |
| `reqshift.py` | the CLI that wires the four together |
| `app.py` | the web UI's server: job queue, stage polling, the same four modules |
| `ui/index.html` | the whole interface, one self-contained file |
| `viewer.py` | read-only browser for reports already on disk |

## Limits, honestly

- **Nine audits, not one.** `verify.py` checks every cardinality against its own
  sentence, `verify_quantities()` does the same for capacity, demand, duration and
  deadlines, and `verify_structure()` audits the DEPENDENCIES: does the sentence really
  say this participant cannot succeed without that one, and is the multiplicity right.
  The third matters most, because every finding is made of dependencies rather than of
  numbers. An unsupported dependency is **kept and flagged**, never removed. Removal was
  tried first and the first real specification disproved it: 9 of 26 dependencies went and
  a substation spec came back with **zero problems**. A false alarm can be traced to a
  sentence and dismissed. Silence cannot be inspected.
  `verify_decomposition()` audits the AND/OR/XOR breakdown inside each actor and which
  goal is its root, and `verify_recall()` asks the opposite question from all the
  others: **what does the document describe that the model does not contain?** Every
  other audit is blind to an omission, and an omission is what turns a real defect into
  a clean bill of health. Nothing from that pass is ever added to the model.
  `verify_maximums()` is its twin and closes the gap the minimum audit left behind.
  Measured across four readings of one 83 page specification, the audited field agreed on
  **17 of 17** participants and the unaudited one on **12 of 17**. Same field type, same
  document, same runs, and the only difference was the audit. That flag is not cosmetic:
  `gaps.build` raises a cardinality gap exactly when `hi_stated` is false, so one reading
  said the maximum was unstated for 50% of participants and another said 90%, and the gap
  counts followed them, 14 against 21. **The deliverable's headline number moved because
  that flag moved.** Nothing is invented when the document is silent, and a document that
  appears to give a maximum below the audited minimum is left unstated on purpose, so the
  contradiction reaches the reader instead of being quietly resolved.
  `verify_minimums()` audits the one field nothing used to check, the MINIMUM, which is
  what decides whether a finding exists at all: `lo = 0` permits a system built with none
  of them, `lo = 1` leaves nothing to find. And `verify_dep_recall()` audits the edge that
  was never drawn. Two fresh readings of one 83 page specification agreed on 86% of
  participants and 79% of bounds and still agreed on **0%** of the findings, because one
  of them never drew a single dependency into the participant that carried the defect, and
  an actor nothing depends on cannot block anything. That pass proposes missing edges in
  goal names the model already contains, confirms each one in a separate call that was
  never told to look hard, and adds only an edge that arrives **with a quote**. Added
  edges are marked `added` and named in the report, so a finding resting on a recovered
  edge is never presented as one the extraction found.
- **Every added edge then gets the stricter reading.** The recall audit's confirming pass
  was never given the four traps `S_SYSTEM` names, and on a fresh substation document it
  accepted *"data concentrators must be required in **exceptional cases** where there is a
  limited capability of the gateway"* as a hard dependency, which is the same
  alternative-read-as-dependency shape that produced the one false positive this project
  has on record. So `verify_structure` runs again, **scoped to the added edges only**, and
  it rejected exactly that one while upholding the other seven. The scoping is not
  tidiness: re-running that pass over already settled edges flipped one from `unsupported`
  back to `ok` with nothing about the edge changed, which would have erased a mark a
  finding rested on. **A pass this movable may add doubt to a claim. It may not remove
  one.** A rejected edge is kept, not deleted, and marked `added-then-rejected`, the
  loudest mark the tool has, because three passes disagree about it and a finding is
  standing on it.
- **The flag travels to the claim.** Flag-not-remove was only half a policy for as long
  as the flag stopped at the edge. On the 83 page substation specification the structure
  audit flagged `BCPU_Measurement -> MFM_Root` with the right reason, that the
  multifunction meter is an optional substitute for the bay unit rather than something it
  depends on, and the one finding built on that edge was published as a **proved defect**
  anyway, in two independent runs. The audit never missed it. The flag went into a banner
  counting nine flagged dependencies and nothing carried it forward. So `analyze.provenance()`
  walks every finding back through the causes it is made of. A finding resting on an
  unsupported dependency, on one an audit added, or on an absence the document never
  states in writing is **unconfirmed**, not proved, and it carries the audit's own reason
  and the sentence next to the claim in the report, the CLI and the UI. The solver result
  does not change and is not in doubt. What the mark separates is *proved of the model*
  from *true of the document*, and only the second is worth sending to anyone.
  The same walk covers the structure INSIDE an actor. A finding says a participant cannot
  meet its overall goal, and that failure travels from the goal the dependency hangs off
  up through the breakdowns above it, so an **unsupported breakdown on that route**, or a
  **root the audit could not settle or reads differently**, marks the finding too. It is
  scoped to the route on purpose: a doubtful breakdown in another branch of the same
  actor, or in another actor entirely, has nothing to do with this failure, and marking
  everything would make the mark mean nothing. Across the whole saved corpus that scoping
  excludes every flagged breakdown and root there is, because each one sits in an actor
  no finding is about.
- **Gaps are ranked by what they can change, not only by where they sit.** `rank_by_effect()`
  probes the solver: does it matter whether any of these exist, and does the maximum matter.
  A gap that can change nothing is demoted and says so. No model call, and it costs
  milliseconds. The second exists because those feed findings that read like measurements
  ("capped at 6"), so an unchecked one is more damaging than an unchecked bound, not
  less. A number that fails is **removed, not corrected**. Measured on the bottling
  line: 4 of 4 invented numbers rejected, 4 of 4 supported numbers accepted.
- **The extraction will sometimes be wrong.** It misreads a cardinality, attaches a goal
  to the wrong actor, or invents a link. This is why the model goes to the canvas for
  review before anyone acts on it. Reviewing a drawing takes two minutes. Drawing one
  from scratch takes two hours. That is the whole value proposition, and it is a smaller
  claim than "AI builds your model".
- **Only what GoalShift can express.** No timing, no resource counts, no probabilities,
  no soft goals. `lo` must be 0 or 1, and XOR takes exactly two children. Real
  manufacturing requirements are full of "within 200ms" and "no more than 4 concurrent",
  and none of that survives. Extending the encoding to SMT would be the way in.
- **Sequencing is lost.** "First A, then B" becomes an AND. The model usually notices
  and says so in its notes, which is the right behaviour, but it is still a real gap.
- **The `notes` field is worth reading every time.** It is where the model records what
  it was unsure about, and in practice it is the most useful part of the output.

## Example

`examples/welding_cell.txt` is a plausible robotic welding cell specification. Nothing in
it looks wrong to a reader. Run it and the solver proves that in 8 of 20 configurations
some piece of equipment is present and cannot do its job, including the minimum
configuration the cell boots into, because two requirement sentences set upper bounds on
robots and vehicles without ever setting a lower one.

`examples/welding_cell.report.md` is the output, kept for reference.

## Replaying a run

Extraction costs one to ten minutes and a real API call, which makes it a slow way to
check a UI change or to show somebody the two steps. `bench/ui_harness.py` serves the real
`ui/index.html` with a finished run handed to it, and proxies step 2 to a running `app.py`
so the solver genuinely re-runs:

```
py -3 app.py                                       in one terminal
py -3 bench/ui_harness.py runs/bottling.job.json   in another, then open :8022
```

`runs/` holds four real runs captured from the pipeline, one per example worth showing.
Capture another with `curl "http://127.0.0.1:8020/api/job?id=<id>" > runs/name.job.json`.

## PDF input

```
py -3 intake.py spec.pdf --report     what was read, and what was cleaned up
py -3 bench/pdf_roundtrip.py          the test that says whether it worked
```

Drop a PDF on the web UI, or give one to the CLI. `intake.py` does the reading with
**pdfplumber**, chosen because it is layout aware and MIT licensed. **PyMuPDF is
deliberately not used. It is AGPL and would poison a commercial product**, and it
happens to be installed on this machine, so do not reach for it.

**Why this is not two lines of pdfplumber.** The report promises every finding links
back to the sentence it came from, and naive extraction breaks that promise three ways,
each one seen on real documents:

- **Running heads splice into sentences.** A sentence crossing a page break comes back
  as "the controller shall SPEC-7720 Rev B 3 only consider a bottle filled", so it is in
  the document and not in the extraction, and the citation never resolves. Lines are
  therefore built from word geometry, edge lines that repeat across pages are removed,
  and a page boundary is never treated as a paragraph boundary.
- **Words break at line ends.** `oper-` plus `ating` is not `operating` until the hyphen
  is healed.
- **Every line is its own line.** Wrapping is undone, but headings, clause numbers and
  paragraph breaks survive, because the extraction depends on that structure.

Whatever was done is reported back rather than done silently. On a 67 page EU deliverable
that reads: 49 running header lines removed, 95 words rejoined, 599 sentences unwrapped.

`bench/pdf_roundtrip.py` is the test that matters. It prints three specifications to
PDFs built to break extraction, a running header and footer on every page, a narrow page
so paragraphs wrap, a short page so sentences are cut in half, reads them back, and
checks that **every sentence and every eight word window of the original is still
findable**. All three pass at 100%.

A scanned PDF holds pictures of words rather than words, and is refused with that
explanation rather than an empty result. There is no OCR.
