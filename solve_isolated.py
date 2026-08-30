"""Run the solver in a separate process, and never lose an extraction to it.

    python solve_isolated.py <spec.json> <out.json> [--smt] [--goalshift DIR]

On 25 August 2026 a UI run of the 83 page substation specification spent twenty
minutes on extraction and nine audits, reached the solver, and died inside z3:

    C.append(z3.And(n[t] >= lo, n[t] <= hi))
    OSError: exception: access violation reading 0x0000000480000267

with `z3types.Z3Exception: b'invalid dec_ref command'` alongside it in the log.
That pair is the signature of z3's native reference counting being driven from a
thread it does not expect. `app.py` runs each job on a worker thread while the
HTTP server answers polls on others, and Python's garbage collector can free a z3
AST on whichever thread happens to hold the GIL.

It did not reproduce in isolation: the same model, on a worker thread, three times,
came back clean, and the CLI has never hit it because the CLI is single threaded.
So it is a race that needs twenty minutes of subprocess churn and GC pressure to
show itself, and chasing it would be expensive and uncertain.

Isolation makes the whole class of failure impossible instead. The solver gets a
fresh interpreter with one thread, nothing else touching z3, and a context that
dies with the process. It also means a native crash can no longer take the server
down with it, which is the more serious version of this bug: an access violation
inside a thread can kill the whole process, and the only reason the server survived
is that this one happened to surface as a Python OSError.

The cost is one process spawn and a JSON round trip, against a solve that already
takes seconds to minutes.
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def solve(spec, smt=False, goalshift_dir=None, timeout=900):
    """Analyse `spec` in a child process. Returns the same dict `analyze` returns.

    A crash in the child is reported as an ordinary failed result rather than
    raised, because the caller's job is to tell the reader the solver could not
    finish, not to fall over as well.
    """
    import tempfile
    d = tempfile.mkdtemp(prefix="reqshift-solve-")
    spec_path = os.path.join(d, "spec.json")
    out_path = os.path.join(d, "result.json")
    with io.open(spec_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(spec))

    cmd = [sys.executable, os.path.join(HERE, "solve_isolated.py"),
           spec_path, out_path]
    if smt:
        cmd.append("--smt")
    if goalshift_dir:
        cmd += ["--goalshift", goalshift_dir]

    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "errors": [
            "The solver did not finish within %d seconds. The model is probably "
            "larger than this analysis can carry. The extracted model is kept, so "
            "nothing has to be read again." % timeout]}

    if os.path.exists(out_path):
        with io.open(out_path, encoding="utf-8") as f:
            return json.load(f)

    # No result file: the child died before it could write one. On Windows a
    # native access violation shows up as a large unsigned exit code, so the
    # number is reported rather than swallowed.
    tail = (p.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-4:]
    return {"ok": False, "errors": [
        "The solver process stopped before it produced a result (exit code %s). "
        "This is a fault in the solver, not in your document, and the extracted "
        "model has been kept so nothing has to be read again." % p.returncode
    ] + [t for t in tail if t]}


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    spec_path, out_path = argv[1], argv[2]
    smt = "--smt" in argv
    gs = argv[argv.index("--goalshift") + 1] if "--goalshift" in argv else None

    sys.path.insert(0, HERE)
    with io.open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    if smt:
        import analyze_smt
        result = analyze_smt.analyze(spec, gs)
    else:
        import analyze
        result = analyze.analyze(spec, gs)
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
