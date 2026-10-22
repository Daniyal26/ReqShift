"""ReqShift web UI.

    py -3 app.py            then open http://localhost:8020

A small local server, because the browser alone cannot do this job: calling Claude
needs a credential, and a credential cannot live in a page you double-click. That is
the one reason ReqShift is not a single self-contained file the way GoalShift is.

Extraction takes a minute or two, so work runs on a background thread and the page
polls for stage updates rather than hanging on one long request.
"""
import argparse
import json
import os
import socket
import sys
import threading
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import analyze
import analyze_smt
import extractor
import gaps
import intake
import prescreen
import solve_isolated
import verify
import report
import schema

JOBS = {}
JOBS_LOCK = threading.Lock()

# Limits for the numbers a reader types in at step 2. Measured, see /api/reanalyze.
MAX_INSTANCES = 20          # of any ONE actor. 20 costs 14 seconds, 22 costs 70.
MAX_CONFIGURATIONS = 20000  # across the whole model.

STAGES = [
    ("read", "Reading the requirements"),
    ("screen", "Checking the document is in scope"),
    ("extract", "AI drafts a goal model"),
    ("check", "Checking the model is well formed"),
    ("audit", "Auditing what each number counts"),
    ("solve", "GoalShift proves what follows"),
    ("write", "Writing the findings up"),
]


def set_stage(job_id, stage, **extra):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job:
            job["stage"] = stage
            job.update(extra)


def _keep_model(job_id, spec, trace):
    """Write a finished extraction to disk so a later failure cannot waste it.

    Twenty minutes of reading and auditing an 83 page specification was thrown
    away by a solver crash, and the model it had already produced was correct and
    sitting in memory the whole time. Anything that reaches this point can be
    re-analysed with `reqshift.py --spec`, which calls no language model at all.
    """
    try:
        d = os.path.join(HERE, "out_recovered", str(job_id)[:8])
        os.makedirs(d, exist_ok=True)
        for name, obj in (("model.spec.json", spec), ("model.trace.json", trace)):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(json.dumps(obj, indent=1))
        return os.path.relpath(d, HERE).replace(os.sep, "/")
    except Exception:
        return None


def run_job(job_id, text, explain, backend, goalshift_dir, engine="sat",
            screening=True, verifying=True):
    try:
        set_stage(job_id, "read")

        # Layer 0. Ten real documents were all out of scope, and each cost 230 to
        # 624 seconds of extraction to discover that. Worse, an out-of-scope model
        # can reach the solver with billions of configurations and hang this job
        # forever. Ask first, in about ten seconds.
        screen = None
        if screening:
            set_stage(job_id, "screen")
            try:
                screen = prescreen.prescreen(text, backend=backend)
            except Exception as e:
                set_stage(job_id, "screen", screen_error=str(e))
            if screen and not screen["in_scope"]:
                set_stage(job_id, "done", state="out_of_scope", screen=screen,
                          reason=screen.get("reason", ""))
                return

        set_stage(job_id, "extract", screen=screen)
        extracted = extractor.extract(text, backend=backend)

        set_stage(job_id, "check")
        shape = schema.shape_errors(extracted)
        if shape:
            set_stage(job_id, "done", state="error", errors=shape,
                      error_kind="malformed", raw=extracted)
            return
        spec, trace = schema.to_spec(extracted)

        # Layer 2b. 95% of extracted bounds were unsupported by the text. A wrong
        # number is worse than none, because the solver treats it as fact.
        # Every audit below catches BROADLY on purpose. They were catching only
        # `extractor.ExtractionError`, and on 25 August a `claude` CLI call hung and
        # raised `subprocess.TimeoutExpired` after 1800 seconds, which slipped past
        # that handler and destroyed a run that had already cost twenty minutes.
        # An audit is an improvement to the model, never a gate on it: one that
        # cannot finish should cost its own contribution and nothing else.
        #
        # Each one also checkpoints the spec it produced. The spec used to be stored
        # once, before any audit ran, so a later failure recovered the raw extraction
        # and threw away the expensive half. That recovery came back with 8,192
        # configurations where the audited model gives a few hundred.
        audit = None
        maudit = None
        min_changed, min_unstated = [], []
        xaudit = None
        max_changed, max_unstated, max_refused = [], [], []
        qaudit = None
        saudit = None
        structure_changed, structure_fixed, structure_flagged = [], [], []
        daudit = None
        decomp_fixed, decomp_flagged = [], []
        recall = None
        draudit = None
        dep_added, dep_rejected, dep_added_rejected = [], [], []
        if verifying:
            set_stage(job_id, "audit", spec=spec, trace=trace)
            try:
                audit = verify.verify(spec, trace, text, backend=backend)
                if any(r.get("verdict") != "ok" for r in audit["results"]):
                    spec, _changed = verify.apply_verdicts(spec, audit["results"])
                    set_stage(job_id, "audit", spec=spec)
            except Exception as e:
                set_stage(job_id, "audit", audit_error=str(e))

            # The minimum, which decides whether there is a finding at all and was
            # the one field nothing checked. Two readings of the same document
            # disagreed on it while agreeing 90% on the participants themselves.
            try:
                maudit = verify.verify_minimums(spec, trace, text, backend=backend)
                if maudit["results"]:
                    spec, min_changed, min_unstated =                         verify.apply_minimum_verdicts(spec, maudit["results"])
                    set_stage(job_id, "audit", spec=spec)
            except Exception as e:
                set_stage(job_id, "audit", minimum_audit_error=str(e))

            # The maximum, the twin of the pass above. `hi_stated` decides which
            # participants become a cardinality gap and nothing audited it, so the
            # gap count moved between readings of one unchanged document.
            try:
                xaudit = verify.verify_maximums(spec, trace, text, backend=backend)
                if xaudit["results"]:
                    spec, max_changed, max_unstated, max_refused =                         verify.apply_maximum_verdicts(spec, xaudit["results"])
                    set_stage(job_id, "audit", spec=spec)
            except Exception as e:
                set_stage(job_id, "audit", maximum_audit_error=str(e))

            # The other numbers, audited for the same reason. An unchecked capacity
            # produces a finding that reads "capped at 6", which sounds measured.
            try:
                qaudit = verify.verify_quantities(spec, trace, text, backend=backend)
                if qaudit["results"]:
                    spec, dropped = verify.apply_quantity_verdicts(spec, qaudit["results"])
                    set_stage(job_id, "audit", spec=spec)
            except Exception as e:
                set_stage(job_id, "audit", quantity_audit_error=str(e))

            # And the shape. Every finding is made of dependencies, so an invented
            # one invents a defect and a missing one hides the defect the customer
            # is paying for. This was the last unguarded layer.
            try:
                saudit = verify.verify_structure(spec, trace, text, backend=backend)
                if saudit["results"]:
                    spec, structure_fixed, structure_flagged = \
                        verify.apply_structure_verdicts(spec, saudit["results"])
                    structure_changed = structure_fixed + structure_flagged
                    set_stage(job_id, "audit", spec=spec)
            except Exception as e:
                set_stage(job_id, "audit", structure_audit_error=str(e))

            # The breakdown inside each actor, and which goal is its root. A wrong
            # operator is corrected; anything unsupported is flagged rather than
            # removed, because removing a breakdown makes a goal a leaf and a leaf
            # is trivially satisfied, which HIDES defects.
            try:
                daudit = verify.verify_decomposition(spec, trace, text, backend=backend)
                if daudit["results"]:
                    spec, decomp_fixed, decomp_flagged = \
                        verify.apply_decomposition_verdicts(spec, daudit["results"])
                    set_stage(job_id, "audit", spec=spec)
            except Exception as e:
                set_stage(job_id, "audit", decomp_audit_error=str(e))

            # And the dependency the extraction never drew. A fresh pair of readings
            # of the same specification agreed on every bound and still disagreed on
            # every finding, because one of them missed a single edge and an actor
            # with no edge into it cannot block anything. This proposes and then
            # confirms, and adds only what arrives with a quote.
            try:
                draudit = verify.verify_dep_recall(spec, trace, text, backend=backend)
                if draudit["results"]:
                    spec, trace, dep_added, dep_rejected =                         verify.apply_dep_recall_verdicts(spec, trace, draudit)
                    # The confirming pass above never got the four traps S_SYSTEM
                    # names, and it accepted an exception-case fallback as a hard
                    # dependency on ElectraNet. Every added edge gets the stricter
                    # reading, scoped to those edges so a settled verdict elsewhere
                    # cannot be flipped and a mark quietly lost.
                    if dep_added:
                        gate = verify.verify_structure(
                            spec, trace, text, backend=backend,
                            only=[k for k, _m, _q, _w in dep_added])
                        spec, _gfixed, dep_added_rejected = \
                            verify.apply_structure_verdicts(spec, gate["results"])
                        set_stage(job_id, "audit", spec=spec, trace=trace)
            except Exception as e:
                set_stage(job_id, "audit", dep_recall_error=str(e))

            # And what the extraction missed, which every audit above is blind to.
            # Reported, never applied: a participant this pass proposes would need
            # goals, a root and bounds that no second opinion should invent.
            try:
                recall = verify.verify_recall(spec, trace, text, backend=backend)
            except Exception as e:
                set_stage(job_id, "audit", recall_error=str(e))

        # The engine follows the model, not a dropdown. A stated minimum above one
        # cannot be expressed in SAT at all, and capacity or timing would be
        # silently ignored by it, which is worse than being refused.
        engine_reason = None
        if engine == "sat":
            want, why = analyze_smt.engine_for(spec)
            if want == "smt" and analyze_smt.available():
                engine, engine_reason = "smt", why
            elif want == "smt":
                engine_reason = ("z3 is not installed, so " + why
                                 + ". Those numbers were left out of the analysis.")
                for a in spec["actors"]:
                    if int(a.get("lo", 0)) > 1:
                        a["lo"] = 1          # or GoalShift refuses the model outright

        gap_list = gaps.build(spec, (audit or {}).get("results"), trace)
        # Severity says what a missing number is CONNECTED to. This says whether it
        # can change the answer at all, which is the question a reader has, and it
        # is answered by the solver rather than by a rule of thumb.
        try:
            # Every solve goes through the same door. One rule with no exceptions
            # is the only version of this that stays true: the first fix covered the
            # job path, missed these two, and the crash came straight back through
            # the one the reader actually clicks.
            analyzer = (lambda sp: solve_isolated.solve(
                sp, smt=(engine == "smt"), goalshift_dir=goalshift_dir))
            gap_list = gaps.rank_by_effect(spec, gap_list, analyzer)
        except Exception:
            pass                      # ranking is an improvement, never a gate
        # After the ranking, and outside the try, because a ranking that failed is
        # still a gap list that must carry its marks.
        gaps.attach_provenance(gap_list, spec, trace)
        gaps_md = gaps.to_markdown(gap_list, "this specification", screen) if gap_list else None

        set_stage(job_id, "solve", spec=spec, trace=trace, audit=audit,
                  gaps=gap_list, gaps_markdown=gaps_md, quantity_audit=qaudit,
                  structure_audit=saudit, structure_changed=structure_changed,
                  structure_flagged=structure_flagged, minimum_audit=maudit, maximum_audit=xaudit,
                  max_changed=max_changed, max_unstated=max_unstated,
                  max_refused=max_refused,
                  minimum_changed=min_changed, minimum_unstated=min_unstated,
                  decomp_audit=daudit, decomp_fixed=decomp_fixed,
                  decomp_flagged=decomp_flagged, recall=recall,
                  dep_recall=draudit, dep_added=dep_added, dep_rejected=dep_rejected,
                  dep_added_rejected=dep_added_rejected,
                  engine=engine, engine_reason=engine_reason)
        # The solver runs in its own process. z3's native reference counting is
        # driven from whichever thread the garbage collector happens to be on, and
        # this server hands each job to a worker while answering polls on others.
        # On 25 August that combination killed a run after twenty minutes of
        # extraction and audits, inside `z3.And(n[t] >= lo, n[t] <= hi)`, with an
        # access violation and an `invalid dec_ref command` beside it in the log.
        # It never reproduced in isolation, so it is a race rather than a bug with
        # an address, and a separate interpreter makes the whole class impossible.
        # It also stops a native crash taking the server down with the job.
        result = solve_isolated.solve(spec, smt=(engine == "smt"),
                                      goalshift_dir=goalshift_dir)
        if not result.get("ok"):
            # The extraction and nine audits cost minutes and real money, so they
            # are written to disk before the error is reported. A solver failure
            # must never mean reading the document again.
            kept = _keep_model(job_id, spec, trace)
            set_stage(job_id, "done", state="error", errors=result["errors"],
                      error_kind="invalid", spec=spec, trace=trace, engine=engine,
                      kept_model=kept)
            return
        found = analyze.findings(spec, result)
        if engine == "smt":
            # Ceilings and deadline shortfalls are solved for, so they only exist here.
            found += analyze_smt.extra_findings(spec, result, goalshift_dir)
        # After the extras, so one pass covers both engines. Carries every audit flag
        # from the dependency it sits on to the findings that rest on it.
        analyze.provenance(spec, trace, found)
        summary = analyze.summary(spec, result, found)
        brief = report.digest(spec, result, found, trace)

        writeup = None
        if explain:
            set_stage(job_id, "write")
            try:
                writeup = extractor.explain(brief, backend=backend)
            except Exception as e:
                writeup = None
                set_stage(job_id, "write", writeup_error=str(e))

        md = report.markdown(spec, result, found, trace, "pasted requirements", writeup)
        set_stage(job_id, "done", state="done", spec=spec, trace=trace, result=result,
                  findings=found, summary=summary, writeup=writeup, markdown=md,
                  engine=engine, engine_reason=engine_reason, screen=screen,
                  audit=audit, quantity_audit=qaudit, structure_audit=saudit,
                  structure_changed=structure_changed,
                  structure_flagged=structure_flagged, minimum_audit=maudit, maximum_audit=xaudit,
                  max_changed=max_changed, max_unstated=max_unstated,
                  max_refused=max_refused,
                  minimum_changed=min_changed, minimum_unstated=min_unstated,
                  decomp_audit=daudit,
                  decomp_fixed=decomp_fixed, decomp_flagged=decomp_flagged,
                  dep_recall=draudit, dep_added=dep_added, dep_rejected=dep_rejected,
                  dep_added_rejected=dep_added_rejected,
                  recall=recall, gaps=gap_list, gaps_markdown=gaps_md)
    except extractor.ExtractionError as e:
        set_stage(job_id, "done", state="error", errors=[str(e)], error_kind="backend")
    except Exception:
        # Same reasoning. Whatever broke, the model already built is worth more
        # than the traceback, so it is kept before the error is reported.
        kept = None
        try:
            with JOBS_LOCK:
                j = JOBS.get(job_id) or {}
                sp, tr = j.get("spec"), j.get("trace")
            if sp:
                kept = _keep_model(job_id, sp, tr)
        except Exception:
            pass
        set_stage(job_id, "done", state="error", error_kind="crash",
                  kept_model=kept, errors=[traceback.format_exc(limit=3)])


class Handler(BaseHTTPRequestHandler):
    server_version = "ReqShift"

    def log_message(self, *a):
        pass

    # ---- plumbing ---------------------------------------------------------
    def _json(self, obj, code=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path, ctype):
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    # ---- routes -----------------------------------------------------------
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._file(os.path.join(HERE, "ui", "landing.html"),
                              "text/html; charset=utf-8")
        if u.path in ("/app", "/app/", "/app/index.html"):
            return self._file(os.path.join(HERE, "ui", "index.html"),
                              "text/html; charset=utf-8")
        if u.path in ("/reqshift.css", "/components.js"):
            # ReqShift's own design system and component module. They are separate
            # files rather than another 800 lines inside index.html, and separate
            # from shared/ because shared/ is GoalShift's too.
            name = os.path.basename(u.path)
            kind = "text/css" if name.endswith(".css") else "application/javascript"
            return self._file(os.path.join(HERE, "ui", name), kind + "; charset=utf-8")
        if u.path.startswith("/shared/"):
            # The design system lives one level up, outside this project, because
            # GoalShift links the same files.
            name = os.path.basename(u.path)
            root = os.path.join(os.path.dirname(HERE), "shared")
            path = os.path.join(root, name)
            kind = {"css": "text/css", "js": "application/javascript"}.get(
                name.rsplit(".", 1)[-1])
            if not kind or not os.path.exists(path):
                return self._json({"error": "not found"}, 404)
            return self._file(path, kind + "; charset=utf-8")
        if u.path == "/api/backends":
            return self._json({"backends": extractor.available_backends(),
                               "model": extractor.MODEL,
                               "smt": analyze_smt.available()})
        if u.path == "/api/examples":
            out = []
            d = os.path.join(HERE, "examples")
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".txt"):
                    text = open(os.path.join(d, fn), encoding="utf-8").read()
                    # Two files can share a first line, so the label comes from the
                    # filename and the first line becomes the tooltip.
                    label = fn[:-4].replace("_", " ").replace("casestudy", "case study")
                    out.append({"name": fn, "words": len(text.split()),
                                "title": label,
                                "subtitle": text.strip().splitlines()[0][:90]})
            return self._json({"examples": out})
        if u.path == "/api/example":
            fn = os.path.basename(q.get("name", [""])[0])
            p = os.path.join(HERE, "examples", fn)
            if not fn.endswith(".txt") or not os.path.exists(p):
                return self._json({"error": "not found"}, 404)
            return self._json({"text": open(p, encoding="utf-8").read()})
        if u.path == "/api/job":
            with JOBS_LOCK:
                job = dict(JOBS.get(q.get("id", [""])[0], {}))
            if not job:
                return self._json({"error": "no such job"}, 404)
            return self._json(job)
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = self._body()
        except Exception as e:
            return self._json({"error": f"bad request: {e}"}, 400)

        if u.path == "/api/analyze":
            text = (body.get("text") or "").strip()
            if not text:
                return self._json({"error": "empty"}, 400)
            job_id = uuid.uuid4().hex[:12]
            with JOBS_LOCK:
                engine = body.get("engine") or "sat"
                stages = [{"id": s, "label": l} for s, l in STAGES]
                # The page shows whatever the server says, so name the engine here or
                # the solve step claims GoalShift ran when z3 did.
                screening = body.get("screen", True) is not False
                verifying = body.get("verify", True) is not False
                for st in stages:
                    if st["id"] == "solve" and engine == "smt":
                        st["label"] = "z3 proves what follows"
                if not screening:
                    stages = [st for st in stages if st["id"] != "screen"]
                if not verifying:
                    stages = [st for st in stages if st["id"] != "audit"]
                if not body.get("explain"):
                    stages = [st for st in stages if st["id"] != "write"]
                JOBS[job_id] = {"id": job_id, "state": "running", "stage": "read",
                                "stages": stages,
                                "explain": bool(body.get("explain")),
                                "engine": engine}
            t = threading.Thread(target=run_job, daemon=True, args=(
                job_id, text, bool(body.get("explain")),
                body.get("backend") or "auto", self.server.goalshift_dir,
                body.get("engine") or "sat", screening, verifying))
            t.start()
            return self._json({"id": job_id})

        if u.path == "/api/read":
            # A PDF arrives base64 encoded in JSON, because multipart parsing in
            # BaseHTTPRequestHandler is more code than this whole route. The text
            # goes back to the page rather than straight into a job, so the reader
            # sees what was actually read out of their document before paying for
            # an extraction. On a scan they see nothing, which is the truth.
            import base64
            name = os.path.basename(body.get("name") or "document.pdf")
            try:
                raw = base64.b64decode(body.get("data") or "", validate=True)
            except Exception:
                return self._json({"error": "That upload was not readable."}, 400)
            if len(raw) > 25 * 1024 * 1024:
                return self._json({"error": "That file is larger than 25 MB."}, 400)
            try:
                got = intake.read_pdf(name, data=raw)
            except intake.IntakeError as e:
                return self._json({"error": str(e)}, 400)
            except Exception as e:
                return self._json({"error": f"That PDF could not be read: {e}"}, 400)
            return self._json({"name": name, "text": got["text"],
                               "pages": got["pages"], "notes": got["notes"],
                               "words": len(got["text"].split())})

        if u.path == "/api/reanalyze":
            # Re-run the solver on an edited model. No language model involved.
            #
            # This is step 2 of the two-step flow. Step 1 tells the customer which
            # quantities their document never states; they supply those numbers and
            # this route proves what follows from them. The numbers now come from the
            # only party who actually knows them, so nothing here is invented.
            spec = body.get("spec")
            engine = body.get("engine") or "sat"
            trace = body.get("trace") or {}

            # Experiment A died on models with 10^13 configurations, every one of them
            # caused by a bound nobody had checked. A person typing numbers into the
            # step 2 form can do the same thing by hand, so refuse before the solver
            # hangs and say which number is responsible.
            #
            # Two separate limits, both measured on this machine rather than guessed.
            # The binding one is INSTANCES OF A SINGLE ACTOR, because GoalShift gives
            # every instance its own variables and the clause count roughly quadruples
            # for every two more: 16 instances is 0.26M clauses and a second, 18 is
            # 1.0M and 4.6s, 20 is 4.2M and 14s, 22 is 16.8M and 70s. Past that it
            # exhausts memory rather than finishing. The configuration product matters
            # too, but far less.
            space, widest, most = 1, None, None
            for a in (spec or {}).get("actors", []):
                lo, hi = int(a.get("lo", 0)), int(a.get("hi", 0))
                name = a.get("label") or a.get("type")
                span = max(0, hi - lo) + 1
                space *= span
                if widest is None or span > widest[1]:
                    widest = (name, span)
                if most is None or hi > most[1]:
                    most = (name, hi)
            if most and most[1] > MAX_INSTANCES:
                return self._json({"state": "error", "errors": [
                    f"{most[0]} at {most[1]} is more than this engine can enumerate. "
                    f"GoalShift reasons about every instance separately, so the encoding "
                    f"grows exponentially in that number and stops being tractable above "
                    f"about {MAX_INSTANCES}. Either give the range you actually care "
                    f"about, which is usually small, or switch the engine to z3, which "
                    f"counts instead of enumerating."]})
            if space > MAX_CONFIGURATIONS:
                return self._json({"state": "error", "errors": [
                    f"Those numbers describe {space:,} configurations, which is more than "
                    f"can be enumerated one at a time. The widest range is {widest[0]} at "
                    f"{widest[1]} possible counts. Narrow it and try again."]})

            try:
                result = solve_isolated.solve(
                    spec, smt=(engine == "smt"),
                    goalshift_dir=self.server.goalshift_dir)
            except Exception as e:
                return self._json({"error": str(e)}, 400)
            if not result.get("ok"):
                return self._json({"state": "error", "errors": result["errors"]})
            found = analyze.findings(spec, result)
            if engine == "smt":
                found += analyze_smt.extra_findings(spec, result,
                                                    self.server.goalshift_dir)
            # Answering the gap questions re-solves, so the marks have to be carried
            # again. A re-run that dropped them would quietly promote an unconfirmed
            # finding to a proved one.
            analyze.provenance(spec, trace, found)
            # The report has to be rebuilt too. Handing back a download written from
            # the pre-answer model would be a quietly wrong document.
            supplied = body.get("supplied") or {}
            source = "pasted requirements"
            if supplied:
                source += (f", with {len(supplied)} "
                           f"{'quantity' if len(supplied) == 1 else 'quantities'} "
                           f"supplied by the reader")
            md = report.markdown(spec, result, found, trace, source)
            return self._json({"state": "done", "result": result, "findings": found,
                               "summary": analyze.summary(spec, result, found),
                               "markdown": md})

        if u.path == "/api/save":
            # Write a finished run to disk, same layout the CLI produces.
            outdir = os.path.join(HERE, "out_ui")
            os.makedirs(outdir, exist_ok=True)
            for fn, content in (("model.spec.json", json.dumps(body.get("spec"), indent=1)),
                                ("model.trace.json", json.dumps(body.get("trace"), indent=1)),
                                ("report.md", body.get("markdown") or "")):
                with open(os.path.join(outdir, fn), "w", encoding="utf-8",
                          newline="\n") as f:
                    f.write(content)
            return self._json({"saved": outdir})

        return self._json({"error": "not found"}, 404)


def main():
    ap = argparse.ArgumentParser(description="ReqShift web UI")
    ap.add_argument("--port", type=int, default=8020)
    ap.add_argument("--goalshift", default=None)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    # Refuse to start on a port something else already holds. The default here allows
    # address reuse, so without this check a second server binds happily alongside the
    # first, the stale one keeps answering, and you debug code that is not running.
    probe = socket.socket()
    try:
        if probe.connect_ex(("127.0.0.1", a.port)) == 0:
            print(f"Something is already serving on port {a.port}. Stop it, or pass "
                  f"--port with a free one.")
            return 1
    finally:
        probe.close()

    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    srv.goalshift_dir = a.goalshift
    url = "http://localhost:%d" % a.port
    backends = extractor.available_backends()
    print("=" * 60)
    print("  ReqShift  ->  " + url)
    print("  backend:  " + (", ".join(backends) if backends else
                            "NONE. Sign in to Claude Code or set ANTHROPIC_API_KEY."))
    print("  engines:  GoalShift (SAT)" +
          ("  and  z3 (SMT)" if analyze_smt.available() else
           "   [z3 missing, SMT unavailable]"))
    print("  Ctrl+C to stop.")
    print("=" * 60)
    if not a.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        srv.server_close()


if __name__ == "__main__":
    main()
