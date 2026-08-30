# ReqShift accuracy project, linear plan

Written 2026-08-24. The goal is one thing stated precisely: **the goal model the AI drafts
should contain everything the document describes, and nothing it does not.**

## The frame, corrected by Phase 0

The plan below was written expecting an omission problem. Four things can be missing from a
drafted model, and only one of them had a recall audit.

| what can be missing | audited for precision | audited for recall |
|---|---|---|
| actors and their cardinalities | yes (`verify`, `verify_minimums`) | no (`verify_recall` reports, never applies) |
| dependencies and their cardinalities | yes (`verify_structure`) | partly (`verify_dep_recall`) |
| decompositions and roots | yes (`verify_decomposition`) | none at all |
| quantities (capacity, demand, duration) | yes (`verify_quantities`, drops only) | no |

**That table is still true and it is no longer the point.** Phase 0 measured the omission rate
and found it small. A single reading finds nearly everything four readings agree on. What it
does instead is INVENT, and it invents at a rate nobody had measured: 31% of dependency edges
and 41% of breakdowns come from exactly one reading in four.

So the governing sentence changes. It was *"an omission produces a clean bill of health"*, which
is true and was the right worry when nothing audited recall. The measured problem is the other
one. **An invention produces a defect that is not there, and it is wrong in the direction that
sells, which is the direction nobody checks.** That is the same failure the OPTCL false positive
already demonstrated once by hand. Phase 0 says it is systemic rather than a one off.

## Where RAG fits, and where it does not

Settled, and Phase 0 settled it against building anything.

The document already fits in context. OPTCL is 25,672 words, roughly 35k tokens, and every call
sees all of it. Retrieval solves "the document does not fit", which is not the problem here, and
top-k chunks would REMOVE material the model currently sees. The one time context was narrowed
on purpose, the old `verify_structure` judged a dependency from its cited sentence alone and
deleted 9 of 26 real dependencies.

The **chunking** half was the half worth having, and it was worth having for recall. Phase 0
shows recall is not the bottleneck, so an exhaustive per-section sweep would spend real money to
fix a problem that is not there, and would worsen the one that is, because more proposals means
more inventions.

Two uses survive, neither of them classic RAG. **Quote grounding**, where an extracted quote is
checked by exact string match against the source before it enters the trace, which kills
fabricated quotes as a class and needs no embeddings. And **multi-document input**, if a customer
ever sends a spec plus annexes plus referenced standards, at which point the window really is
exceeded.

---

## Phase 0. DONE 2026-08-24. It contradicted this plan, which is why it went first.

`bench/recall.py`, built and run over the four independent OPTCL readings on disk
(`optcl`, `optcl2`, `repeat1`, `repeat2`). No API cost. Baseline saved at
`runs/recall_baseline_optcl.txt`.

Method: there is no annotated ground truth, so the UNION of independent readings stands
in for it, and **consensus** means an element a strict majority proposed. Recall against
consensus carries a **structural floor**: a consensus element is by definition held by
3 of 4 readings, so 75% is scored before anything is measured. The floor is printed
beside every number, because without it these look far better than they are.

| | recall vs consensus | margin over floor | proposed by exactly ONE of 4 |
|---|---|---|---|
| participants | 97% | +22 | **5%** (1 of 21) |
| dependencies | 93% | +18 | **31%** (13 of 42) |
| decompositions | 86% | +11 | 41% (20 of 49), and Phase 2 showed this is mostly a paraphrase artifact |

**THE PREMISE OF THIS PLAN WAS WRONG. RECALL IS NOT THE PROBLEM. PRECISION IS.**

A single reading finds nearly everything the other readings agree on. What it also does
is invent. Nearly a third of all dependency edges and **two fifths of all breakdowns**
were proposed by exactly one reading out of four. The singleton share is uncircular,
unlike the recall figure, and it is the real result.

**And the dependency recall audit did not help.** Scored against the same consensus,
repeat1 has 27 edges at 86%. After `verify_dep_recall`, it has 30 edges and **still
86%**. It added three edges and recovered **zero** that the other readings agree exist.
That matches what the audit's own OPTCL run already showed, where five recovered edges
changed nothing at all.

### What this rules out

Phase 2 as written, an exhaustive chunked sweep for recall, would attack a problem that
is not there and would make the real one worse, because more proposals means more
inventions. **Do not build it.** The same applies to a decomposition recall pass. The
retrieval question is settled with it: chunking was the only half worth having, and it
was worth having for recall, which turns out not to be the bottleneck.

### What this points at instead

1. **Dependencies, 31% singletons.** Precision work, which is exactly the direction the
   added-edge gate took on 2026-08-24. Extend it: every edge, not only added ones,
   should have to survive a reading that is trying to reject it.
2. **Decompositions, 41% singletons, and a question that has to be answered first.**
   `verify_decomposition` already audits these for precision, and 41% survive anyway.
   Before treating that as a defect, test the alternative explanation: **how a goal is
   broken into sub-goals is a modelling CHOICE, not a fact in the document.** Two
   competent engineers decompose differently. Cardinality is a fact and can be checked
   against a sentence. Decomposition may not be, in which case measuring it the same way
   is a category error and the honest fix is to stop treating breakdown disagreement as
   error at all. **Answer this before building anything.**
3. **Participants are fine.** 5% singletons, 97% recall. Leave them alone.

## Phase 1. Gaps carry their provenance. No API cost.

Unchanged, and now the clear next build. Findings learned this on 2026-08-24, gaps did
not, and gaps are the deliverable.

Proved live: the single **critical** gap in `out_electranet` is Condition Monitor,
justified as *"supplies Substation SCADA Gateway, and the specification allows there to
be none at all"*. That rests on one dependency, `GwConditionMeasurements ->
CmMonitorPlantCondition`, which the structure audit flagged **unsupported**. It is the
only edge into that participant, so both the reason and the critical severity exist only
because of an edge the tool's own audit rejected. The gap report says nothing about it.

Phase 0 sharpens why this matters. If a third of edges are seen by one reading in four,
then gaps and findings resting on a single unconfirmed edge are the normal case, not the
exception.

## Phase 2. DONE 2026-08-24. Decomposition is a CHOICE, and the 41% was mostly an artifact.

Answered by reading all 20 singleton breakdowns by hand against the document, then
re-measuring without goal names. Both halves of the hypothesis were right.

**Most of the 41% was a measurement artifact.** The decomposition row is keyed by GOAL
LABEL, and a goal is free prose. The same GPS root goal came back from four readings as
*"synchronise the entire SAS to UTC"*, *"provide co-ordinated universal time to the
substation"*, *"provide station wide time synchronisation"* and *"provide UTC traceable
time synchronisation"*. Word overlap under the 0.5 threshold splits one goal into four
elements and calls two of them singletons. The same happened to the event printer, the
communication gateway and the PLCC equipment. A participant is a proper noun and barely
paraphrases, which is why that row is trustworthy at 5%. A goal is a sentence and
paraphrases constantly, which is why this one was not.

**Measured again without reading any goal name, by tree shape per participant:**

| | |
|---|---|
| agree the participant's goal is broken down at all, versus a leaf | **100%** (16 of 16) |
| agree on the exact shape (breakdown count, operators, branching) | **12%** (2 of 16) |

That is the signature of a modelling choice. **Whether a participant does work that
decomposes is a fact in the document. How you carve it up is not.** Two competent
engineers produce different trees from the same paragraph and neither is wrong.

**And the variance is largely inert.** Breakdown counts are stable across readings (25 to
30) and the operator mix is stable and AND dominant. repeat1 and repeat2 return **8
outcome classes each** despite 28 versus 25 breakdowns and only 12% shape agreement. What
moves the class count is the BOUNDS, which drove configurations from 288 to 3,456. Shape
variance did not reach the output where it could be isolated. That is suggestive at n=4
with confounds, not proof.

### Confirmed by controlled experiment, 2026-08-24

`bench/decomp_sensitivity.py`, result at `runs/decomp_sensitivity.txt`. No API cost. The
n=4 observation above was four readings differing in several ways at once, so nothing
was isolated. This holds actors, bounds, dependencies, roots and operators FIXED and
changes only the shape of the trees, in ways whose logic is provably identical.

| perturbation | behaviour |
|---|---|
| deepen: `AND[a,b,c]` becomes `AND[a, X]` with `X = AND[b,c]` | **identical, 7 of 7** |
| flatten: the reverse, inlining a child AND | **identical, 3 of 3** |
| round trip, deepen then flatten | **identical, 7 of 7** |
| relax each AND to OR in turn | **only 8 of 84 nodes move anything (10%)** |

**Granularity is provably inert and the operator layer is nearly inert too.** On the
substation models only 1 or 2 of every 21 to 24 AND nodes change any outcome when
relaxed. That is why 12% shape agreement sits happily beside a stable class count, and
it is a property of the ENCODING rather than of the extraction, so no AI is involved in
the claim.

Two things this explains that looked like bugs. A single control flip kept returning
IDENTICAL on the substation models, because relaxing an AND can only make a goal easier
to satisfy and most ANDs are never false anywhere, so one picked at random is inert nine
times in ten. And a real bug it did surface: the first `flatten` walked a snapshot of the
decomposition list and could reach a node that had already been inlined and deleted,
deleting its children's breakdowns while the real parent still pointed at them. The
engine refused the dangling model, which is how it was caught.

### Consequence, and it removes work rather than adding it

**Do not build a decomposition precision pass, and do not chase breakdown disagreement.**
It is not error, it is granularity, and `verify_decomposition` already catches the cases
where a breakdown is genuinely unsupported. The right treatment is disclosure, which the
gap report and the findings already do through the `unsupported-breakdown` mark added
earlier today.

`bench/recall.py` now prints the shape measure and marks the label-keyed decomposition row
as untrustworthy, so nobody reads 41% as an invention rate again.

## Phase 3. Dependency precision. DESIGNED AND COSTED 2026-08-24, not yet built.

The 31% singleton rate is the one accuracy number that is real rather than an artifact,
because dependencies are keyed by participant pairs and not by prose. Two free
measurements settled how to attack it.

### The existing audit already discriminates, so do not build a new one

For each reading, its singleton edges (the ones no other reading drew) were checked
against that same reading's own structure audit.

| | flagged unsupported |
|---|---|
| singleton edges, the likely inventions | **10 of 14 (71%)** |
| consensus edges, the likely real ones | **13 of 60 (22%)** |

The audit is not blind. It catches most inventions and it is roughly three times more
likely to flag an invented edge than a real one. **But it is a signal, not a separator.**
Deleting everything it flags would remove 13 real edges to kill 10 invented ones, which
is precisely the trade that once emptied a real specification and returned no problems at
all. Flag-not-remove was right, and as of 2026-08-24 the flag reaches the claim.

Caveat on the table: `optcl.job.json` was produced under the old removal policy, so its
unsupported edges were already deleted and its 0% flag rate is not comparable. Excluding
it the split is 71% against 28%, which is the same conclusion.

### The remedy that IS worth paying for: two readings, intersected

Simulated over the six pairs available from the four saved readings.

| | |
|---|---|
| one reading alone, share of its edges that are consensus edges | **55%** |
| two readings intersected, share that are consensus edges | **83%** |
| consensus edges surviving the intersection | **86%** |

**Be careful reading the first two rows.** An edge only one reading drew cannot appear in
two, so removing single-reading inventions is true by construction rather than by
measurement. The number that is a genuine measurement is the third: requiring two
readings to agree costs only **14% of the edges most readings agree on**. That is the
cost side, and it is small.

**Design.** Extract twice, intersect the dependency sets by participant pair, keep the
intersection, and mark rather than delete what only one reading drew, exactly as added
edges are marked now. Cost is one extra extraction. On the OPTCL run extraction was 456
of 1,127 seconds, so roughly 40% more wall clock, and no extra audit calls because the
audits run once on the merged model.

**BUILT 2026-08-24** as `corroborate.py` with `--corroborate` on the CLI, and validated
offline against the two fresh readings at no API cost: 21 of 21 participants matched,
**32 of 41 edges corroborated and 9 not**. Nothing is deleted, an uncorroborated edge is
marked and the mark reaches findings and gaps like every other.

**Does it fix the critical gap? Partly, and the shortfall found the last cause.** Dropping
uncorroborated edges, as an experiment rather than the policy, correctly killed reading
one's critical, which rested on an uncorroborated edge. Reading two's survived, so they
still disagree.

**The remaining cause is the AND against XOR choice, and it is the same trap as the edge
level false positive.** The multifunction meter is identical in both readings, same
bounds, same single incoming edge at the same multiplicity, flagged unsupported in both.
What differs is the path from the depending goal to the participant's root: one reading
has **XOR** then AND, so the root is satisfiable the other way and the meter is inert;
the other has **AND** straight to the root, so the meter is required. The sentence says
the meter *"may be provided ... if monitoring is not available in the BCPU"*, which is an
alternative, so the XOR is right and the AND is wrong.

**Checked, and the audit was right.** `verify_decomposition` left that AND alone
deliberately. The breakdown was audited against *"the unit should be capable of
protection, measurement, control and record"*, and against that sentence AND is plainly
correct: the participant really must do measurement monitoring. The sentence that causes
the trouble is attached to the CHILD GOAL, not to the breakdown.

**So the defect was always the EDGE**, and the structure audit flags it `unsupported` in
BOTH readings. The two models are two defensible encodings of one alternative: one puts it
in the operator, so the root is satisfiable without the meter and the bad edge is
neutralised, and the other puts it in the edge, so the bad edge reaches a critical gap.
Neither is wrong about the document.

**And both critical gaps carry the mark.** One cites its teleprotection edge, the other
cites the meter edge, both scoped to severity. The 0% critical agreement is real, and every
critical is disclosed as resting on a dependency no sentence states, so a reader of either
report is told not to trust it without checking that sentence.

**No new audit is needed here.** Phase 2's conclusion stands unqualified after all: do not
build a decomposition operator pass.

## Phase 4. Audit the MAXIMUM. Diagnosed 2026-08-24, and it has its own control.

Phase 0 measured which ELEMENTS a reading finds. It never measured whether the NUMBERS
on them agree, and the numbers are what the gap report is made of. Measured now, free,
over participants three or more readings found.

| field | agreement |
|---|---|
| `lo`, the minimum | **93%** |
| `hi`, the maximum | 67% |
| `lo` and `hi` together | 60% |
| `hi_stated` | **53%** |

**The experiment already contains its own control, by accident.** `lo` is audited by
`verify_minimums`. `hi` has never been audited by anything. Judged on the two readings
that both carry the flag:

| | |
|---|---|
| `lo_stated`, audited | **identical 17 of 17 (100%)** |
| `hi_stated`, never audited | identical 12 of 17 (71%) |

Same field type, same document, same two runs, and the only difference is that one of
them has an audit behind it.

**And `hi_stated` is what the deliverable is built from.** `gaps.build` raises a
cardinality gap when `hi_stated` is False. What each reading claims about the maximum on
the same specification:

| reading | "the document states no maximum" | gaps reported |
|---|---|---|
| optcl | 10 of 18 (56%) | 12 |
| optcl2 | 18 of 20 (90%) | 21 |
| repeat1 | 10 of 20 (50%) | 14 |
| repeat2 | 14 of 21 (67%) | 23 |

The extraction's own claim about whether the document gives a maximum swings from 50% to
90% on one unchanged document, and the gap count follows it. **That is the cause of the
46% cardinality spine.** It is not that participants are missed, since recall against
consensus is 97%. It is that the flag deciding whether each one becomes a gap is a coin
toss nobody audits.

**So Phase 4 is not "cardinality recall". It is `verify_maximums`**, the exact twin of
the pass that took `lo` to 93% and `lo_stated` to 100%. Narrow question per participant,
same shape as `M_SYSTEM`: does the document state an upper bound for this, and what is
it. For every actor, not only those the extraction already doubted, because the flag
itself is what moves.

**VALIDATED 2026-08-24 on a fresh pair of full runs.** `verify_maximums` built and wired,
two independent readings of OPTCL, comparison pre-registered in `bench/bounds_agreement.py`
before the runs finished. Result at `runs/maximums_validation.txt`.

| | baseline | fresh pair | |
|---|---|---|---|
| `lo` | 100% | 100% | control, unchanged |
| `lo_stated` | 100% | 100% | control, unchanged |
| `hi` | 79% | **90%** | **+12** |
| `hi_stated` | 74% | **90%** | **+17** |
| "the document states no maximum" | 50% against 67% | **48% against 48%** | identical |

The flag that swung from 50% to 90% across earlier readings now reads the same on both.
The two controls did not move, which is what makes the other two credible.

**What it did NOT fix, and the prediction that failed.** The gap count was predicted to
stop swinging. It did not: 11 against 26, and the single critical gap is a DIFFERENT
participant in each reading. The cardinality spine improved only from 46% to 54%.

The cause is now unambiguous and it is Phase 5. Split by kind, the two readings produced
**9 against 11 cardinality gaps**, the audited half, and **2 against 15 quantity derived
gaps**, which is the entire remaining swing. Reading one extracted **0 capacity fields
and 2 durations**, reading two extracted **2 and 14**. A demand gap only exists where a
capacity was found, so zero capacities means zero demand gaps and the report is silently
shorter.

**Verdict: keep the pass.** It moved the field it was built for by 17 points while both
controls held. **Do not claim the gap report is reproducible.** Its headline is still not.

## Phase 5. DONE 2026-08-24. One gap per provider. Gap agreement 27% to 65%.

The swing left after the maximum audit was 11 against 26, and splitting it by kind showed
9 against 11 cardinality gaps, which is fine, against 2 against 15 quantity derived ones,
which was the whole problem. Two structural causes, neither of them extraction quality.

**Demand gaps were raised per DEPENDENCY.** A provider with a stated capacity and five
dependers produced five gaps, and the same provider with no capacity produced none, so the
report's length tracked whether a capacity number happened to be extracted. The readings
extracted 0 and 2 capacities and produced 0 and 10 demand gaps.

**The measurement that decided the redesign:** which providers are SHARED agreed **88%**
between readings, while the extracted capacity NUMBERS agreed essentially not at all. So
the gap is keyed on the dependency graph rather than on extraction luck. `quantity_gaps`
now emits **one gap per provider**, worded by what is known, and skips a provider whose
capacity could never bind.

**Timing gaps were extraction luck and provably inert.** All low severity, no deadline in
either model, and the file already said durations without a deadline are never used. Now
one gap for the whole model naming the participants that carry durations.

| | before | after |
|---|---|---|
| held-out pair, all gaps | 14 against 23, **27%** | 19 against 18, **54%** |
| fresh pair, all gaps | 11 against 26 | 19 against 24, **65%** |
| capacity and demand | 0 against 10, 0% | 9 against 12, **75%** |
| timing | 17% | **100%** |

The held-out pair is the one this was NOT developed against, and it still doubled. The
eight bottling demos are unchanged at two gaps each.

**Re-measured with `rank_by_effect` on, which is what the product does.** Ranking is
cheap, 3.4 and 47.1 seconds, so there is no reason to measure without it.

| | baseline | fresh pair, ranked |
|---|---|---|
| all gaps | 27% | **65%** |
| critical and high | 25% | **43%** |
| **critical only** | 0% | **still 0%** |

**The critical gap is still not reproducible**, and the earlier impression that it was
came from measuring without ranking. One reading calls PLCC critical, the other calls the
multifunction meter critical.

**The cause is not the gap set, which is the useful part.** Both participants are gaps in
BOTH readings, and the probe's verdict is an exact mirror image: run one says the meter
changes no outcome and PLCC does, run two says the reverse. So the ranking is working and
the two MODELS genuinely disagree about which participants are load bearing. That traces
to dependency structure, 41 against 40 edges with a 31% singleton rate.

**So the last unreproducible number in the deliverable is downstream of Phase 3**, which
is designed and costed above and not built.

## Phase 6. Re-measure, then decide about voting. API cost.

- Re-run Phase 0 on fresh readings and compare every number to the baseline.
- Re-run `bench/repeat.py`, which now reports gaps split by kind and by severity band.
- Only then consider N-way voting on the audits, which multiplies the cost of everything and
  should be a last resort rather than a first instinct.

---

## The measurement targets, in one place

Baselines from OPTCL repeat1 vs repeat2, 2026-08-24.

| | now | this project should move it |
|---|---|---|
| participants | 86% | Phase 2 |
| bounds on matched | 79% | Phase 4 |
| dependency shape | 55% | Phases 2, 4 |
| gaps, cardinality spine | 46% | Phases 2, 4 |
| gaps, quantity derived | 8% | Phase 5 |
| gaps, critical band | **0%** | all of it |
| findings | 0% | all of it |

## What this project cannot fix, and should not pretend to

**You have exactly one real in-scope document.** OPTCL. Everything above is validated against a
single Indian substation tender, and the customer genre is German machine builders. Recall work
does not need an in-scope document, so ElectraNet, BHEL, ABB and et200sp are all usable test
material, but **reproducibility tuned on one document in the wrong genre may not transfer.**

That is not a reason to stop. It is a reason to keep the phases measured and reversible, and to
treat the first real customer specification as the event that re-validates all of it.
