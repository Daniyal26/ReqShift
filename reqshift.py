"""ReqShift - requirements prose in, analysed goal model out.

    py -3 reqshift.py examples/welding_cell.txt

The pipeline, and which half of it is trustworthy:

    requirements text
        |  Claude               <- a draft, needs review
    goal model (GoalShift spec)
        |  GoalShift + SAT      <- proved
    behavior classes, statechart, findings
        |  Claude               <- rewording of proved facts only
    report

GoalShift itself is imported and never touched.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze
import extractor

# A quoted sentence from a real specification carries curly quotes, and a Windows
# console is cp1252, so printing one killed the run after the audit that produced
# it had already been paid for. Replace what the console cannot draw rather than
# losing the work.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import intake
import report
import schema


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="reqshift",
        description="Extract a goal model from requirements text and analyse it with "
                    "GoalShift.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="The extracted model is a draft. Review it on the GoalShift canvas "
               "before trusting the shape of it. The analysis of whatever model you "
               "approve is exact.")
    p.add_argument("input", nargs="?",
                   help="a .pdf, .txt or .md file of requirements, or - for stdin. "
                        "Omit it when using --spec.")
    p.add_argument("-o", "--outdir", default="out",
                   help="where to write the results (default: out)")
    p.add_argument("--backend", default="auto", choices=["auto", "sdk", "cli"],
                   help="how to reach Claude. 'cli' uses your Claude Code sign-in and "
                        "needs no API key (default: auto)")
    p.add_argument("--model", default=extractor.MODEL, help="model id for extraction")
    p.add_argument("--goalshift", default=None,
                   help="path to the GoalModelTool folder (default: ../GoalModelTool)")
    p.add_argument("--smt", action="store_true",
                   help="analyse with the z3 integer backend instead of GoalShift. "
                        "Lifts lo>1 and makes wide cardinality ranges free, but the "
                        "result is no longer proved by the thesis encoding.")
    p.add_argument("--explain", action="store_true",
                   help="also have Claude write the findings up in prose. It may only "
                        "reword what the solver proved.")
    p.add_argument("--spec", default=None,
                   help="skip extraction and analyse an existing GoalShift spec JSON")
    p.add_argument("--force", action="store_true",
                   help="extract even if the pre-screen says the document is out of "
                        "scope. The pre-screen costs seconds and extraction costs "
                        "minutes, so only use this when you disagree with it.")
    p.add_argument("--no-verify", action="store_true",
                   help="skip the second pass that audits what each extracted number "
                        "actually counts. Not recommended: 95%% of bounds failed that "
                        "audit on real documents.")
    p.add_argument("--corroborate", action="store_true",
                   help="read the document a SECOND time and mark every dependency the "
                        "second reading did not also draw. 31%% of edges are drawn by "
                        "only one reading, which is the most common way this tool "
                        "invents something. Costs one extra extraction.")
    p.add_argument("--gaps-only", action="store_true",
                   help="stop after the gap report. Answers 'what does this "
                        "specification fail to specify' without running any solver.")
    args = p.parse_args(argv)
    if not args.input and not args.spec:
        p.error("give a requirements file, or --spec to re-analyse an existing model")

    os.makedirs(args.outdir, exist_ok=True)
    # A report titled "spec" tells the reader nothing about which document it came
    # from. When re-analysing a saved model the run directory is the useful name,
    # since that is what the earlier run was called.
    if args.spec:
        _d = os.path.basename(os.path.dirname(os.path.abspath(args.spec)))
        name = _d or os.path.basename(args.spec)
    else:
        name = os.path.basename(args.input)
    screen = None

    # ---- 1. get a model -----------------------------------------------------
    if args.spec:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
        trace = {"notes": []}
        beside = os.path.join(os.path.dirname(os.path.abspath(args.spec)),
                              "model.trace.json")
        if os.path.exists(beside):
            with open(beside, encoding="utf-8") as f:
                trace = json.load(f)
        print(f"Loaded an existing model from {args.spec}")
    else:
        try:
            text = sys.stdin.read() if args.input == "-" else _read(args.input)
        except intake.IntakeError as e:
            print(f"\n{e}", file=sys.stderr)
            return 2
        if not text.strip():
            p.error("the input is empty")
        backends = extractor.available_backends()
        chosen = args.backend if args.backend != "auto" else (backends[0] if backends else None)

        # ---- 0. is this document even worth extracting? ---------------------
        # Ten real documents, ten out of scope, and extraction cost 230 to 624
        # seconds each to find that out. This asks first, in about ten.
        # The screen runs even under --force. It costs about ten seconds and its
        # verdict is worth keeping as a LABEL even when the answer is "carry on":
        # `gaps.to_markdown` prints a scope note when the screen said no, and
        # skipping the screen threw that note away on exactly the documents that
        # needed it most. Measured 2026-08-25: four refused documents all produced
        # substantial gap reports, and the two that drifted into category errors
        # were the ones a scope note would have warned about.
        if True:
            import prescreen as _ps
            print(f"Checking whether {name} is in scope...")
            try:
                screen = _ps.prescreen(text, backend=args.backend, model=args.model)
            except extractor.ExtractionError as e:
                print(f"  pre-screen unavailable, continuing anyway. {e}",
                      file=sys.stderr)
            if screen and not screen["in_scope"]:
                _write(os.path.join(args.outdir, "prescreen.json"),
                       json.dumps(screen, indent=1))
            if screen and not screen["in_scope"] and args.force:
                print("  out of scope, and continuing anyway because --force "
                      "was given.")
                print("  " + str(screen["reason"]))
                print("  the gap report will say so, because a gap in a document "
                      "that was never written to state quantities may be "
                      "deliberate.")
            elif screen and not screen["in_scope"]:
                print(f"\nOut of scope. {screen['reason']}")
                print("\nThis document does not state how many of its parts exist, so a "
                      "configuration analysis has nothing to work with.")
                print("Run again with --force to extract anyway, or with --gaps-only "
                      "to report what it fails to specify.")
                if not args.gaps_only:
                    return 6
            elif screen:
                print(f"  in scope ({screen.get('confidence')} confidence): "
                      f"{screen['reason']}")

        print(f"Reading {name} ({len(text.split())} words) with {args.model} "
              f"via the {chosen} backend...")
        try:
            extracted = extractor.extract(text, backend=args.backend, model=args.model)
        except extractor.ExtractionError as e:
            print(f"\nExtraction failed.\n{e}", file=sys.stderr)
            return 2

        shape = schema.shape_errors(extracted)
        if shape:
            print("\nThe extracted model is malformed, so it was not analysed:",
                  file=sys.stderr)
            for e in shape:
                print(f"  - {e}", file=sys.stderr)
            _write(os.path.join(args.outdir, "extraction.raw.json"),
                   json.dumps(extracted, indent=2))
            print(f"\nThe raw extraction is in {args.outdir}/extraction.raw.json "
                  f"if you want to fix it by hand.", file=sys.stderr)
            return 3

        spec, trace = schema.to_spec(extracted)
        print(f"  extracted {len(spec['actors'])} actor types, "
              f"{len(spec['goals'])} goals, {len(spec['deps'])} dependencies")

    spec_path = os.path.join(args.outdir, "model.spec.json")
    _write(spec_path, json.dumps(spec, indent=1))
    _write(os.path.join(args.outdir, "model.trace.json"), json.dumps(trace, indent=1))

    # ---- 1b. audit the numbers, then report what the document never said ----
    # Citations proved honest across 2,040 elements. Numbers did not: 95% of
    # bounds were unsupported by the text. Checking is cheap, so it is default.
    audit = None
    maudit = None
    mchanged, munstated = [], []
    qaudit = None
    saudit = None
    schanged = []
    daudit = None
    dfixed, dflagged = [], []
    recall = None
    draudit = None
    dep_added, dep_rejected = [], []
    if not args.no_verify and not args.spec:
        import verify as _v
        print("Auditing what each extracted number actually counts...")
        try:
            audit = _v.verify(spec, trace, text, backend=args.backend, model=args.model)
            bad = [r for r in audit["results"] if r.get("verdict") != "ok"]
            print(f"  {len(bad)} of {audit['checked']} bounds are not supported "
                  f"by the document")
            _write(os.path.join(args.outdir, "audit.json"), json.dumps(audit, indent=1))
            if bad:
                spec, changed = _v.apply_verdicts(spec, audit["results"])
                _write(spec_path, json.dumps(spec, indent=1))
                print(f"  {len(changed)} bound(s) replaced with an honest unknown, "
                      f"so the solver is not handed a number the document never gave")
        except extractor.ExtractionError as e:
            print(f"  audit unavailable, the numbers below are unchecked. {e}",
                  file=sys.stderr)

        # The minimum, the field that decides whether a finding exists at all.
        try:
            maudit = _v.verify_minimums(spec, trace, text, backend=args.backend,
                                        model=args.model)
            if maudit["checked"]:
                spec, mchanged, munstated = _v.apply_minimum_verdicts(
                    spec, maudit["results"])
                _write(spec_path, json.dumps(spec, indent=1))
                print(f"  minimums: {len(mchanged)} corrected from the document, "
                      f"{len(munstated)} never stated")
                for lbl, old_lo, new_lo, verdict, quote in mchanged[:8]:
                    print(f"    {lbl}: {old_lo} -> {new_lo}  ({verdict})")
        except extractor.ExtractionError as e:
            print(f"  minimum audit unavailable. {e}", file=sys.stderr)

        # And the maximum, the twin of the pass above. Measured across four readings
        # of one specification, `lo_stated` agreed on 17 of 17 participants once it
        # was audited and `hi_stated` agreed on 12 of 17 because nothing audited it.
        # That flag decides which participants become a gap, so the deliverable's
        # headline count moved with it.
        try:
            xaudit = _v.verify_maximums(spec, trace, text, backend=args.backend,
                                        model=args.model)
            if xaudit["checked"]:
                spec, xchanged, xunstated, xrefused = _v.apply_maximum_verdicts(
                    spec, xaudit["results"])
                _write(spec_path, json.dumps(spec, indent=1))
                _write(os.path.join(args.outdir, "audit.maximums.json"),
                       json.dumps(xaudit, indent=1))
                print(f"  maximums: {len(xchanged)} corrected from the document, "
                      f"{len(xunstated)} never stated")
                for lbl, old_hi, new_hi, quote in xchanged[:8]:
                    print(f"    {lbl}: {old_hi} -> {new_hi}")
                    if quote:
                        print(f'      "{str(quote)[:110]}"')
                for lbl, old_hi, n, lo in xrefused:
                    print(f"    CONTRADICTION {lbl}: the document reads as a maximum "
                          f"of {n} but the audited minimum is {lo}")
                    print(f"      left unstated on purpose, so the gap report asks "
                          f"for it rather than hiding the disagreement")
        except extractor.ExtractionError as e:
            print(f"  maximum audit unavailable. {e}", file=sys.stderr)

        # The same audit for capacity, demand, duration and a deadline. Those feed
        # findings that read like measurements ("capped at 6"), so an unchecked one
        # is more damaging than an unchecked cardinality, not less.
        try:
            qaudit = _v.verify_quantities(spec, trace, text, backend=args.backend,
                                          model=args.model)
            if qaudit["checked"]:
                qbad = [r for r in qaudit["results"] if r.get("verdict") != "ok"]
                print(f"  {len(qbad)} of {qaudit['checked']} capacity or timing "
                      f"numbers are not supported by the document")
                _write(os.path.join(args.outdir, "audit.quantities.json"),
                       json.dumps(qaudit, indent=1))
                if qbad:
                    spec, dropped = _v.apply_quantity_verdicts(spec, qaudit["results"])
                    _write(spec_path, json.dumps(spec, indent=1))
                    for key, val, what, verdict, measures in dropped:
                        print(f"    removed {key.split(':')[0]} {val} on {what}: "
                              f"it measures {measures}")
        except extractor.ExtractionError as e:
            print(f"  quantity audit unavailable. {e}", file=sys.stderr)

        # The shape, which nothing checked until now and which every finding is
        # made of.
        try:
            saudit = _v.verify_structure(spec, trace, text, backend=args.backend,
                                         model=args.model)
            if saudit["checked"]:
                sbad = [r for r in saudit["results"] if r.get("verdict") != "ok"]
                print(f"  {len(sbad)} of {saudit['checked']} dependencies are not "
                      f"supported as extracted")
                _write(os.path.join(args.outdir, "audit.structure.json"),
                       json.dumps(saudit, indent=1))
                if sbad:
                    spec, sfixed, sflagged = _v.apply_structure_verdicts(
                        spec, saudit["results"])
                    schanged = sfixed + sflagged
                    _write(spec_path, json.dumps(spec, indent=1))
                    for key, what, was, now, why in sfixed:
                        print(f"    corrected {key}: {was} -> {now}")
                    for key, what, was, now, why in sflagged:
                        print(f"    FLAGGED {key}: no single sentence states it")
                        if why:
                            print(f"      {why}")
                    if sflagged:
                        print("      kept in the model on purpose. Removing them made a real "
                              "specification come back with no problems at all")
        except extractor.ExtractionError as e:
            print(f"  structure audit unavailable. {e}", file=sys.stderr)

        try:
            daudit = _v.verify_decomposition(spec, trace, text, backend=args.backend,
                                             model=args.model)
            if daudit["checked"]:
                dbad = [r for r in daudit["results"] if r.get("verdict") != "ok"]
                print(f"  {len(dbad)} of {daudit['checked']} breakdowns or roots are "
                      f"not supported as extracted")
                if dbad:
                    spec, dfixed, dflagged = _v.apply_decomposition_verdicts(
                        spec, daudit["results"])
                    _write(spec_path, json.dumps(spec, indent=1))
                    for parent, was, now, why in dfixed:
                        print(f"    corrected {parent}: {was} -> {now}")
                    # `what`, not `name`: a Python for-loop leaks its variable into
                    # the enclosing scope, and this one used to clobber the document
                    # name set at the top of the run. Every report written afterwards
                    # was titled after a flagged breakdown instead of the document.
                    for kind, what, verdict, why in dflagged:
                        print(f"    FLAGGED {kind} {what}: {verdict}. {why or ''}")
                        print(f"      left in the model on purpose, because removing it "
                              f"would hide defects rather than reveal them")
                    if dflagged:
                        print("      any finding that reaches its goal through one of "
                              "these is reported as unconfirmed, not proved")
        except extractor.ExtractionError as e:
            print(f"  breakdown audit unavailable. {e}", file=sys.stderr)

        # The edge the extraction never drew. Two readings of one specification
        # agreed on every bound and disagreed on every finding over a single
        # missing dependency, so this proposes them and then confirms them, and
        # adds only an edge that arrives with a quote behind it.
        try:
            draudit = _v.verify_dep_recall(spec, trace, text, backend=args.backend,
                                           model=args.model)
            if draudit["checked"]:
                spec, trace, dep_added, dep_rejected = _v.apply_dep_recall_verdicts(
                    spec, trace, draudit)
                print(f"  dependency recall: {len(draudit['proposed'])} proposed, "
                      f"{len(dep_added)} confirmed and added, {len(dep_rejected)} rejected")
                for key, mult, quote, why in dep_added:
                    print(f"    ADDED {key} ({mult})")
                    print(f"      \"{quote[:110]}\"")
                if dep_added:
                    _write(spec_path, json.dumps(spec, indent=1))
                    print("      added edges are marked in the model, so a finding that "
                          "rests on one can be traced to the sentence above")
                    # The recall audit's confirming pass was never given the four
                    # traps that S_SYSTEM names, and on ElectraNet it accepted an
                    # exception-case fallback ("data concentrators must be required
                    # in exceptional cases") as a hard dependency, which is the same
                    # shape that produced the OPTCL false positive. So every added
                    # edge goes through the stricter reading before it is trusted.
                    # Scoped to the added edges: this pass is movable enough that
                    # re-judging settled ones could erase a mark rather than add one.
                    try:
                        gate = _v.verify_structure(
                            spec, trace, text, backend=args.backend, model=args.model,
                            only=[k for k, _m, _q, _w in dep_added])
                        spec, gfixed, gflagged = _v.apply_structure_verdicts(
                            spec, gate["results"])
                        _write(spec_path, json.dumps(spec, indent=1))
                        _write(os.path.join(args.outdir, "audit.added_edges.json"),
                               json.dumps(gate, indent=1))
                        print(f"    strict re-reading of the {len(dep_added)} added "
                              f"edge(s): {len(gflagged)} rejected, "
                              f"{len(dep_added) - len(gflagged)} upheld")
                        for key, _w, _was, _now, why in gflagged:
                            print(f"      REJECTED {key}")
                            if why:
                                print(f"        {why}")
                        if gflagged:
                            print("        kept in the model, not removed, because a "
                                  "pass this movable may add doubt to a claim and may "
                                  "not silently delete one. Any finding resting on it "
                                  "is reported as the least trustworthy in the report")
                    except extractor.ExtractionError as e:
                        print(f"    strict re-reading unavailable. {e}", file=sys.stderr)
                if draudit.get("over_cap"):
                    print(f"    {len(draudit['over_cap'])} further proposals were not "
                          f"judged, because the pass is capped at {_v.MAX_PROPOSALS}")
            else:
                print("  dependency recall: nothing proposed, the model has the "
                      "dependencies the document states")
        except extractor.ExtractionError as e:
            print(f"  dependency recall unavailable. {e}", file=sys.stderr)

        try:
            recall = _v.verify_recall(spec, trace, text, backend=args.backend,
                                      model=args.model)
            miss = len(recall["missing_actors"]) + len(recall["missing_deps"])
            print(f"  completeness: {miss} thing(s) the document describes are not in "
                  f"the model")
            for a_ in recall["missing_actors"]:
                print(f"    MISSING participant: {a_.get('name')}")
                print(f"      \"{str(a_.get('sentence'))[:110]}\"")
            for d_ in recall["missing_deps"]:
                print(f"    MISSING dependency: {d_.get('depender')} <- {d_.get('provider')}")
            if miss:
                print("    nothing was added to the model. Review these before trusting "
                      "a clean result")
        except extractor.ExtractionError as e:
            print(f"  completeness audit unavailable. {e}", file=sys.stderr)

    # A second, independent reading, used only to corroborate the dependencies of
    # the first. Nothing is deleted: an uncorroborated edge is marked, exactly as an
    # unsupported one is, because deleting edges was tried once and made a real
    # specification come back with no problems at all.
    if args.corroborate and not args.spec:
        try:
            import corroborate as _c
            print("Reading it a second time to corroborate the dependencies...")
            other = _c.second_reading(text, backend=args.backend, model=args.model)
            spec, ok_, bad_, unjudged = _c.mark_uncorroborated(spec, other)
            _write(spec_path, json.dumps(spec, indent=1))
            print(f"  {len(ok_)} of {len(ok_) + len(bad_)} dependencies were drawn by "
                  f"both readings, {len(bad_)} by only this one")
            if unjudged:
                print(f"  {len(unjudged)} could not be judged, because the second "
                      f"reading has no counterpart for one of their participants")
            if bad_:
                print("      kept in the model and marked, not deleted. A finding or "
                      "gap resting on one says so")
        except extractor.ExtractionError as e:
            print(f"  corroboration unavailable. {e}", file=sys.stderr)

    import gaps as _g
    gap_list = _g.build(spec, (audit or {}).get("results"), trace)
    try:
        import analyze as _an
        gap_list = _g.rank_by_effect(
            spec, gap_list, lambda sp: _an.analyze(sp, args.goalshift))
    except Exception:
        pass                          # ranking is an improvement, never a gate
    # After the ranking, because a cardinality gap's SEVERITY is what rests on the
    # dependencies and the ranking is what sets it. Outside the try, because a
    # ranking that failed is still a gap list that must carry its marks.
    _g.attach_provenance(gap_list, spec, trace)
    if gap_list:
        _write(os.path.join(args.outdir, "gaps.md"),
               _g.to_markdown(gap_list, name, screen))
        _write(os.path.join(args.outdir, "gaps.json"), json.dumps(gap_list, indent=1))
        crit = sum(1 for g in gap_list if g["severity"] == "critical")
        print(f"  {len(gap_list)} unstated quantit{'y' if len(gap_list)==1 else 'ies'}"
              f"{f', {crit} critical' if crit else ''} -> gaps.md")

    if args.gaps_only:
        print(f"\nWritten to {args.outdir}")
        print("  gaps.md                what this specification does not state")
        print("  model.spec.json        the extracted model")
        if audit:
            print("  audit.json             what each number was checked against")
        return 0

    # ---- 2. hand it to a solver --------------------------------------------
    # --smt forces the integer backend. Otherwise the MODEL decides: a stated
    # minimum above one cannot be expressed in SAT, and capacity or timing would
    # be silently dropped by it.
    if not args.smt and not args.spec:
        import analyze_smt as _smt
        want, why = _smt.engine_for(spec)
        if want == "smt" and _smt.available():
            print(f"  using z3 rather than GoalShift: {why}")
            print("   this result is NOT proved by the encoding the thesis describes")
            args.smt = True
        elif want == "smt":
            print(f"  {why}, but z3 is not installed, so those numbers are ignored",
                  file=sys.stderr)
            for a in spec["actors"]:
                if int(a.get("lo", 0)) > 1:
                    print(f"   {a.get('label') or a['type']}: minimum {a['lo']} "
                          f"lowered to 1, which GoalShift can express",
                          file=sys.stderr)
                    a["lo"] = 1

    if args.smt:
        import analyze_smt
        if not analyze_smt.available():
            print("The SMT backend needs z3.  pip install z3-solver", file=sys.stderr)
            return 5
        print("Analysing with the SMT backend (z3)...")
        result = analyze_smt.analyze(spec, args.goalshift)
    else:
        print("Analysing with GoalShift...")
        result = analyze.analyze(spec, args.goalshift)

    if not result.get("ok"):
        print("\nGoalShift rejected the model:", file=sys.stderr)
        for e in result["errors"]:
            print(f"  - {e}", file=sys.stderr)
        _write(os.path.join(args.outdir, "report.md"),
               report.markdown(spec, result, [], trace, name))
        print(f"\nThe model is in {spec_path}. Open it on the GoalShift canvas to fix it.",
              file=sys.stderr)
        return 4

    found = analyze.findings(spec, result)
    if args.smt:
        # Ceilings and deadline shortfalls are solved for, not observed, so they only
        # exist on the SMT path.
        import analyze_smt
        found += analyze_smt.extra_findings(spec, result, args.goalshift)
    # After the SMT extras, so one pass covers both engines. Everything the audits
    # flagged is carried from the edge it was written on to the findings built on
    # it, which is where the reader needs it.
    analyze.provenance(spec, trace, found)
    summary = analyze.summary(spec, result, found)
    print(f"  {summary['configurations']} configurations, "
          f"{summary['classes']} behavior classes, "
          f"{summary['problems']} problem(s) found"
          + (f", {summary['unconfirmed']} of them resting on something the "
             f"document does not state" if summary.get("unconfirmed") else ""))
    if args.smt:
        print(f"  {result['stats']['regions']} regions, "
              f"{result['stats']['sat_calls']} SMT calls  "
              f"(the configuration count was computed, not enumerated)")
        for c in result["classes"]:
            for reg in c.get("regions", []):
                print(f"    class {c['class']} holds when  {reg}")

    # ---- 3. optional prose over proved facts --------------------------------
    brief = report.digest(spec, result, found, trace)
    _write(os.path.join(args.outdir, "findings.txt"), brief)
    writeup = None
    if args.explain:
        print("Writing the findings up...")
        try:
            writeup = extractor.explain(brief, backend=args.backend, model=args.model)
        except extractor.ExtractionError as e:
            print(f"  write-up skipped: {e}", file=sys.stderr)

    md = report.markdown(spec, result, found, trace, name, writeup)
    report_path = os.path.join(args.outdir, "report.md")
    _write(report_path, md)
    _write(os.path.join(args.outdir, "analysis.json"),
           json.dumps({"summary": summary, "findings": found, "result": result}, indent=1))

    _write(os.path.join(args.outdir, "open_in_goalshift.txt"),
           "Open GoalShift (Downloads/GoalModelTool/index.html), press F12 for the\n"
           "console, and paste this one line to draw the model on the canvas:\n\n"
           "loadFromSpec(" + json.dumps(spec) + ")\n")

    print(f"\nWritten to {os.path.abspath(args.outdir)}")
    print(f"  report.md              the readable result")
    print(f"  model.spec.json        the goal model, GoalShift's own format")
    # Not "the proved facts" any more. Some of them are proved of the model and
    # not of the document, and the file says which is which.
    print(f"  findings.txt           what the solver found, plain text")
    print(f"  analysis.json          everything, machine readable")
    print(f"  open_in_goalshift.txt  one line to paste to see it on the canvas")

    # The last thing on the screen is the thing that gets quoted to a customer, so
    # a finding that rests on an unstated input says so here, not only in the
    # report. This is the line that once read as a proved defect and was not one.
    for f in found:
        if f["kind"] == "inert-cardinality":
            continue
        if f.get("proved", True):
            print(f"\n  ! {f['headline']}")
            continue
        print(f"\n  ? {f['headline']}")
        print(f"      UNCONFIRMED. Proved of the model, but the model asserts "
              f"something the document does not.")
        for r in f["rests_on"]:
            print(f"      {r['why']}: {r['what']}")
            if r.get("quote"):
                print(f'        "{r["quote"][:150]}"')
        print("      Read that sentence before this goes in front of anyone.")
    return 0


def _read(path):
    """Read a requirements file. PDFs go through intake, which undoes the things
    that would otherwise stop a finding pointing back at its own sentence."""
    got = intake.read(path)
    for note in got["notes"]:
        print(f"  {note}")
    if got["kind"] == "pdf":
        print(f"  Read {got['pages']} pages, {len(got['text'].split()):,} words.")
    return got["text"]


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    sys.exit(main())
