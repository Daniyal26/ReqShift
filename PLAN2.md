# Next technical phase: more real documents

Written 2026-08-25. Everything measured so far comes from **one document**. OPTCL is the
only specification in 37 that passed the pre-screen on its own merits, and every number
in `PLAN.md` (86/79/55/46/8%, then 90% and 65% after the repairs) was measured on it.
That is the single largest weakness in the whole body of evidence, and it is the one more
documents can fix.

## What more documents actually buy

Not "more testing" in general. Four specific things that cannot be established with one:

1. **Whether the repairs generalise.** `verify_maximums` was validated on one OPTCL pair.
   The gap consolidation was validated on the same pair plus one held-out pair of the same
   document. Neither has ever seen a second specification.
2. **Whether the pre-screen is too strict.** It has refused 36 documents and nobody has
   checked whether it was right to. That is a false-negative rate nobody has measured, and
   it is measured in lost customers.
3. **A real test of `--corroborate`.** It has only ever been smoke-tested on a 210 word
   demo. It has never read a real specification twice.
4. **Whether the findings ever agree across documents.** Three readings of OPTCL named
   three different headline defects. Nobody knows if that is OPTCL or the tool.

---

## Phase A. Acquire. Cheap, mostly manual, no API cost.

**Search by DOCUMENT TYPE, not by industry.** The sharpest result on file is that OPTCL's
own GIS specification and its own general technical volume are both out of scope while its
Substation Automation System specification is in. It is not that power utilities state
composition. It is that a document written to procure **a system assembled from cooperating
devices** states how many of each, and nothing else does, not even from the same buyer.

So search for the phrase, not the sector:

    "substation automation system" specification <utility>
    "SAS" technical specification bay control unit IEC 61850

Utilities that publish tenders openly: POWERGRID, NTPC, WBSETCL, GETCO, MSETCL,
TANTRANSCO, KPTCL, APTRANSCO, RVPN, UPPTCL, and the transmission companies of neighbouring
countries which use the same document conventions.

**POWERGRID first, by hand.** `apps.powergrid.in` refuses connections from here but may
load in a browser. A search snippet quotes it as *"One Bay Control unit shall be provided
for supervision and control of each 765, 400, 220, 132 kV bay"*, which is a stated
cardinality, so it is the strongest single candidate known.

**Before spending anything on a downloaded PDF**, extract the text and count bound phrases
locally: `up to N`, `at least N`, `minimum of`, `maximum of`, `one for each`, `not more
than`, `N nos`. Free, and it sorts the batch. OPTCL had a high count. The GIS specification
had 21 across 40 pages and was refused.

**Deliverable:** eight to twelve candidate documents with text extracted and a phrase count
each.

## Phase B. Screen the batch. About ten seconds and one small call each.

Run `prescreen.py` over all of them and record every verdict with its reason.

**Deliverable:** a table of document, words, phrase count, verdict, reason. Expect most to
be refused. That is the finding, not a failure, and it is already a 37 document result
worth reporting on its own.

## Phase C. Is the pre-screen too strict? No new code. THE VALUABLE ONE.

Nobody has ever checked a refusal. There is already one piece of evidence that the screen
may be over-strict: **ElectraNet was refused, forced anyway, and produced a usable gap
report** with 11 gaps and two findings that were correctly marked unconfirmed.

Take four or five refused documents, force them with `--force`, and judge only the **gap
report**, not the findings:

- Does it name real participants from the document?
- Are the missing quantities genuinely missing, checkable by searching the text?
- Would an engineer at that company find the list worth reading?

**If the answer is usually yes, the product changes shape.** The business direction already
says the gap report is step 1 for any document and the solver analysis is step 2. If the
gap report works on documents the screen refuses, then **the screen should not gate the gap
report at all**. It should gate only the findings, and say so: *this document does not state
its quantities, so there is nothing to prove yet, but here is everything it leaves open.*

That would turn a refusal into a deliverable, which matters more commercially than any
accuracy work left in `PLAN.md`.

**Deliverable:** a yes or no on whether the screen should gate the gap report, with the
forced reports as evidence.

## Phase D. Run the ones that pass. Roughly 30 minutes each.

Full runs on anything that screens in. Keep the job JSON.

**Watch for:** audits skipped (all nine should complete), which engine was chosen and why,
and whether any finding comes back **proved** rather than unconfirmed. Not one has yet on
real material.

## Phase E. Reproducibility on a SECOND document. Two runs of one document.

This is the phase that retires the "one document" caveat. On the best new in-scope
document, run it **twice** and put the pair through the benches that already exist:

    py -3 bench/repeat.py           a.job.json b.job.json
    py -3 bench/recall.py           a.job.json b.job.json ...
    py -3 bench/bounds_agreement.py a/model.spec.json b/model.spec.json

**The numbers to compare against OPTCL**, from `runs/maximums_validation.txt` and
`runs/recall_baseline_optcl.txt`:

| | OPTCL |
|---|---|
| `hi_stated` agreement | 90% after the maximum audit |
| gap report agreement | 65% after the consolidation |
| dependency singletons | 31% |

If a second document lands near those, the repairs generalise and the measurements can be
quoted as properties of the tool. If it lands far away, they are properties of OPTCL and
must be reported that way.

## Phase F. `--corroborate` on real material. One extra extraction.

It has never read a real specification twice. Run the best in-scope document with
`--corroborate` and check the prediction from the simulation: **corroboration should cost
about 14% of the edges most readings agree on** while removing single-reading inventions.

On OPTCL that matters directly. The last run's two findings rested on **four added edges
and one flagged edge**. If corroboration removes edges that only one reading drew, those
findings should either firm up or disappear, and either outcome is informative.

---

## What this phase cannot fix

**It is still substation specifications.** The customer genre is German machine builders,
and a bottling line is not a switchyard. Reproducibility tuned on utility tenders may not
transfer, and the honest position stays: these are properties measured on one genre, and
the first real customer document re-validates all of it.

That is a reason to keep the phases measured and reversible. It is not a reason to skip
them, because one document is a weaker base than several of the wrong kind.
