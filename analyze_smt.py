"""An SMT analysis of the same goal models, with integer cardinalities.

GoalShift is untouched and remains the reference. This is ReqShift's experimental
backend: same models, same answers on the shared fragment, but the actor counts are
z3 integer variables instead of one Boolean per possible instance.

Two things follow from that change.

FIRST, `lo` is no longer restricted to 0 or 1. "At least three robots shall be
present" is expressible here and is rejected outright by the SAT encoding, which
would need a counting encoding for it.

SECOND, and this is the interesting one, the configuration enumeration disappears.
Look at how a count can possibly matter:

    a 1..* dependency holds when  n_provider >= 1  and the provider's goal holds
    a *..* dependency holds when  n_provider == 0  or  the provider's goal holds
    an actor's goals are false when  n_actor == 0

Every one of those tests only asks whether a count is zero or not. Nothing in this
notation can tell two present hospitals from three. So the satisfaction pattern is a
function of the ZERO/NONZERO vector alone, and there are at most 2^k of those for k
actor types, however wide the ranges are. Hospitals 0..3 and hospitals 0..1000000 cost
exactly the same to analyse.

That also explains, rather than merely detects, the "inert cardinality" findings the
SAT path reports empirically. The upper bounds genuinely cannot change any outcome.

ONE ASSUMPTION, stated plainly. This encoding carries one Boolean per goal per actor
TYPE, not per instance, which assumes the present instances of a type can be taken to
behave alike when deciding that type's satisfaction. Instances of a type are
interchangeable and share no constraint with each other, so this is expected to be
exact on the restricted notation, but it is an assumption and not a proof.
`bench/diff_smt.py` is what checks it: it runs both engines over generated models and
compares the full behavior-class result. Do not trust this file on its own word.
"""
import itertools
import os

from analyze import DEFAULT_GOALSHIFT, load_engine


class SmtUnavailable(RuntimeError):
    pass


def _z3():
    try:
        import z3
    except ImportError:
        raise SmtUnavailable("The SMT backend needs z3.  pip install z3-solver")
    return z3


# ---------------------------------------------------------------------------
# Model reading, reusing GoalShift's own normaliser so the two engines can never
# disagree about what the spec says.
# ---------------------------------------------------------------------------

def _model(spec, goalshift_dir=None):
    return load_engine(goalshift_dir).Model(spec)


def validate(M):
    """The SAT engine's rules, minus the ones SMT lifts."""
    errs = []
    if not M.actors:
        errs.append("Add at least one actor type.")
    for t, (lo, hi) in M.actors.items():
        if lo < 0:
            errs.append(f"Actor {t}: lower bound cannot be negative.")
        if hi < 1 or hi < lo:
            errs.append(f"Actor {t}: upper bound must be >= 1 and >= lower bound.")
    for t in M.actors:
        if t not in M.root or not M.root[t]:
            errs.append(f"Actor {t} has no root goal.")
        elif M.owner.get(M.root[t]) != t:
            errs.append(f'Root goal "{M.root[t]}" of actor {t} is not owned by {t}.')
    for g, o in M.owner.items():
        if o not in M.actors:
            errs.append(f'Goal "{g}" is assigned to unknown actor "{o}".')
    for p, (op, cs) in M.decomp.items():
        if p not in M.owner:
            errs.append(f'Decomposition parent "{p}" is not a known goal.')
        if op not in ("AND", "OR", "XOR"):
            errs.append(f'Decomposition of "{p}": operator must be AND, OR or XOR.')
        if op == "XOR" and len(cs) != 2:
            errs.append(f'XOR decomposition of "{p}" needs exactly 2 children.')
        for c in cs:
            if c not in M.owner:
                errs.append(f'Decomposition child "{c}" of "{p}" is not a known goal.')
            elif M.owner.get(c) != M.owner.get(p):
                errs.append(f'Child "{c}" and parent "{p}" must belong to the same actor.')
    for dg, pg, mult in M.deps:
        if dg not in M.owner:
            errs.append(f'Dependency source "{dg}" is not a known goal.')
        if pg not in M.owner:
            errs.append(f'Dependency target "{pg}" is not a known goal.')
        if mult not in ("1..*", "*..*"):
            errs.append(f"Dependency {dg} -> {pg}: multiplicity must be 1..* or *..*.")
    return errs


# ---------------------------------------------------------------------------
# The encoding
# ---------------------------------------------------------------------------

def quantities(spec):
    """The optional numeric fields, all absent from GoalShift's own notation.

    duration  on a goal   how long it takes once its prerequisites are met
    deadline  on an actor its root goal must finish within this
    capacity  on an actor how many units ONE instance can serve
    demand    on a dep    how many units EACH depending instance consumes
    parallel  on a decomp children run together rather than one after another

    Capacity is read in aggregate: the whole depending type against the whole
    providing type, n_D * demand <= n_P * capacity. Per-instance assignment is not
    modelled, so this says whether the group can cope, not who serves whom.
    """
    q = {
        "duration": {g["name"]: float(g["duration"])
                     for g in spec.get("goals", []) if g.get("duration") is not None},
        "deadline": {a["type"]: float(a["deadline"])
                     for a in spec.get("actors", []) if a.get("deadline") is not None},
        "capacity": {a["type"]: int(a["capacity"])
                     for a in spec.get("actors", []) if a.get("capacity") is not None},
        "demand": {(d["from"], d["to"]): int(d["demand"])
                   for d in spec.get("deps", []) if d.get("demand") is not None},
        "parallel": {d["parent"] for d in spec.get("decomp", []) if d.get("parallel")},
    }
    q["used"] = bool(q["duration"] or q["deadline"] or q["capacity"] or q["demand"])
    return q


def engine_for(spec):
    """Which engine this model NEEDS, and why, in words a reader can act on.

    The engine used to be a dropdown, which put the choice on someone who cannot
    know the answer. Two things in a model decide it instead:

      * a stated minimum above one. GoalShift carries one Boolean per possible
        instance and rejects `lo > 1` outright, so this is not a preference, it is
        the difference between an answer and an error.
      * capacity, demand, duration or a deadline. GoalShift does not reject these,
        it IGNORES them, which is worse: the run appears to succeed while the
        numbers the document actually stated play no part in the result.

    Returns (engine, reason). `reason` is None when SAT is genuinely sufficient,
    and SAT stays the default because it is the encoding the thesis proves.
    """
    over = [a for a in spec.get("actors", []) if int(a.get("lo", 0)) > 1]
    if over:
        names = ", ".join((a.get("label") or a["type"]) for a in over[:3])
        return "smt", (f"{names} has a stated minimum above one, which the SAT "
                       f"encoding cannot express")
    q = quantities(spec)
    if q["used"]:
        kinds = [k for k in ("capacity", "demand", "duration", "deadline") if q[k]]
        return "smt", ("this model states " + " and ".join(kinds)
                       + ", which the SAT encoding ignores rather than uses")
    return "sat", None


def build(M, spec=None, include_deadlines=True):
    """Integer counts, one Boolean per goal per actor type, and the constraints."""
    z3 = _z3()
    q = quantities(spec or {})
    n = {t: z3.Int(f"n_{t}") for t in M.order}
    g = {name: z3.Bool(f"g_{name}") for name in M.owner}
    present = {t: n[t] >= 1 for t in M.order}
    C = []

    for t in M.order:
        lo, hi = M.actors[t]
        C.append(z3.And(n[t] >= lo, n[t] <= hi))

    # An absent actor type satisfies nothing.
    for name, owner in M.owner.items():
        C.append(z3.Implies(z3.Not(present[owner]), z3.Not(g[name])))

    # Decomposition, exactly the SAT engine's three operators.
    for parent, (op, children) in M.decomp.items():
        cs = [g[c] for c in children]
        if op == "AND":
            C.append(g[parent] == z3.And(*cs))
        elif op == "OR":
            C.append(g[parent] == z3.Or(*cs))
        else:                                    # XOR, exactly two children
            C.append(g[parent] == z3.Xor(cs[0], cs[1]))

    # Dependencies. This is where a count is read, and only ever for zero-ness.
    for dg, pg, mult in M.deps:
        provider = M.owner[pg]
        if mult == "1..*":
            C.append(z3.Implies(g[dg], z3.And(present[provider], g[pg])))
        else:                                    # *..*  vacuous when none present
            C.append(z3.Implies(g[dg], z3.Or(z3.Not(present[provider]), g[pg])))

    if not q["used"]:
        return n, g, C, q, None

    # ---- capacity ---------------------------------------------------------
    # The whole depending type against the whole providing type. This is the part
    # that makes a cardinality mean something: with capacity in play the answer
    # stops depending only on whether a count is zero.
    for dg, pg, _mult in M.deps:
        w = q["demand"].get((dg, pg))
        cap = q["capacity"].get(M.owner[pg])
        if w is None or cap is None:
            continue
        C.append(z3.Implies(g[dg], n[M.owner[dg]] * w <= n[M.owner[pg]] * cap))

    # ---- timing -----------------------------------------------------------
    # finish[x] is when goal x is met. Constraints are asserted only where the goal
    # actually holds, so an unsatisfied branch never drags a deadline down with it.
    dur = lambda x: q["duration"].get(x, 0.0)
    finish = {name: z3.Real(f"t_{name}") for name in M.owner}
    for name in M.owner:
        C.append(finish[name] >= 0)
        C.append(z3.Implies(g[name], finish[name] >= dur(name)))

    for parent, (op, children) in M.decomp.items():
        if op == "AND" and parent not in q["parallel"]:
            # Sequential is the conservative reading, and this notation has no
            # ordering to tell us otherwise. Mark a decomposition parallel to
            # override it.
            C.append(z3.Implies(g[parent],
                                finish[parent] >= dur(parent)
                                + z3.Sum([finish[c] for c in children])))
        else:
            for c in children:
                C.append(z3.Implies(z3.And(g[parent], g[c]),
                                    finish[parent] >= dur(parent) + finish[c]))

    for dg, pg, _mult in M.deps:
        # Waiting on another actor pushes your own finish out. This is the latency
        # chain, and it is the whole reason timing is worth having.
        C.append(z3.Implies(g[dg], finish[dg] >= finish[pg] + dur(dg)))

    for t, limit in (q["deadline"].items() if include_deadlines else ()):
        if t in M.root:
            C.append(z3.Implies(g[M.root[t]], finish[M.root[t]] <= limit))

    return n, g, C, q, finish


def _pattern_for(M, z3, solver, n, g, occupied, pres=None):
    """Best pattern for one zero/nonzero vector, and how many SAT calls it took.

    Same rule as the SAT engine: the pattern the most actor types can reach in a
    single satisfying assignment, ties broken towards the earlier actor types.
    """
    if pres is None:
        lo_of = {t: M.actors[t][0] for t in M.order}
        pres = []
        for t, on in zip(M.order, occupied):
            pres.append(n[t] >= max(1, lo_of[t]) if on else n[t] == 0)

    live = [k for k, on in enumerate(occupied) if on]
    calls = 0

    def root(k):
        return g[M.root[M.order[k]]]

    feasible = []
    for k in live:
        calls += 1
        if solver.check(*pres, root(k)) == z3.sat:
            feasible.append(k)

    for size in range(len(feasible), -1, -1):
        for sub in itertools.combinations(feasible, size):
            assumps = list(pres)
            for k in live:
                assumps.append(root(k) if k in sub else z3.Not(root(k)))
            calls += 1
            if solver.check(*assumps) == z3.sat:
                return tuple("-" if not occupied[k] else ("OK" if k in sub else "X")
                             for k in range(len(M.order))), calls
    return tuple("-" if not on else "X" for on in occupied), calls


def _region_size(M, occupied):
    """How many concrete configurations a zero/nonzero region contains."""
    total = 1
    for t, on in zip(M.order, occupied):
        lo, hi = M.actors[t]
        total *= (hi - max(1, lo) + 1) if on else 1
    return total


def _region_text(M, occupied):
    bits = []
    for t, on in zip(M.order, occupied):
        lo, hi = M.actors[t]
        if not on:
            bits.append(f"n_{t} = 0")
        else:
            a = max(1, lo)
            bits.append(f"n_{t} = {a}" if a == hi else f"{a} <= n_{t} <= {hi}")
    return " and ".join(bits)


def _counts_str(M, counts):
    names = []
    for t, k in zip(M.order, counts):
        names += [f"{t.lower()}{i}" for i in range(1, k + 1)]
    return "{" + ", ".join(names) + "}" if names else "{}"


# ---------------------------------------------------------------------------
# Public entry point, result-shape compatible with GoalShift's analyze
# ---------------------------------------------------------------------------

MAX_LISTED = 20000
MAX_ENUMERATED = 200000


def analyze(spec, goalshift_dir=None):
    z3 = _z3()
    M = _model(spec, goalshift_dir)
    errs = validate(M)
    if errs:
        return {"ok": False, "errors": errs}

    n, g, C, q, finish = build(M, spec)
    solver = z3.Solver()
    solver.add(*C)

    # Which types may be absent at all, given their lower bound.
    choices = [(False, True) if M.actors[t][0] == 0 else (True,) for t in M.order]

    # Without capacity or timing, a count is only ever read for zero-ness, so the
    # zero/nonzero vector settles the pattern and the ranges cost nothing. Add either
    # and that stops being true, because the actual numbers start to matter.
    smt_calls = 0
    if q["used"]:
        ranges = [range(M.actors[t][0], M.actors[t][1] + 1) for t in M.order]
        space = 1
        for r in ranges:
            space *= len(r)
        if space > MAX_ENUMERATED:
            return {"ok": False, "errors": [
                f"This model uses timing or capacity, so every count has to be "
                f"examined rather than just its zero-ness, and {space:,} "
                f"configurations is more than the {MAX_ENUMERATED:,} cap. Narrow a "
                f"cardinality range, or drop the numeric fields to get the fast path."]}
        counts_to_pattern = {}
        for counts in itertools.product(*ranges):
            pres = [n[t] == c for t, c in zip(M.order, counts)]
            pattern, calls = _pattern_for(M, z3, solver, n, g,
                                          tuple(c > 0 for c in counts), pres)
            counts_to_pattern[counts] = pattern
            smt_calls += calls
        return _result_from_counts(M, spec, z3, n, g, C, q, finish,
                                   counts_to_pattern, smt_calls)

    region_to_pattern = {}
    for occupied in itertools.product(*choices):
        pattern, calls = _pattern_for(M, z3, solver, n, g, occupied)
        region_to_pattern[occupied] = pattern
        smt_calls += calls

    # Number the classes by walking outward from the minimum configuration, which is
    # the same rule the SAT engine uses, so the numbering matches.
    init = tuple(M.actors[t][0] >= 1 for t in M.order)
    pattern_to_class, seen, queue = {}, {init}, [init]
    while queue:
        node = queue.pop(0)
        pat = region_to_pattern.get(node)
        if pat is None:
            continue
        if pat not in pattern_to_class:
            pattern_to_class[pat] = len(pattern_to_class) + 1
        for k in range(len(M.order)):
            nxt = node[:k] + (not node[k],) + node[k + 1:]
            if nxt in region_to_pattern and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    for pat in region_to_pattern.values():
        if pat not in pattern_to_class:
            pattern_to_class[pat] = len(pattern_to_class) + 1

    total = sum(_region_size(M, o) for o in region_to_pattern)

    regions = []
    for occupied in sorted(region_to_pattern, key=lambda o: [int(x) for x in o]):
        pat = region_to_pattern[occupied]
        regions.append({
            "where": _region_text(M, occupied),
            "occupied": [bool(x) for x in occupied],
            "pattern": list(pat),
            "class": pattern_to_class[pat],
            "configurations": _region_size(M, occupied),
        })

    # The concrete configuration table, when the space is small enough to be worth
    # listing. Above the cap the regions carry the same information without it.
    instances, listed = [], total <= MAX_LISTED
    if listed:
        rows = []
        for occupied in region_to_pattern:
            ranges = []
            for t, on in zip(M.order, occupied):
                lo, hi = M.actors[t]
                ranges.append(range(max(1, lo), hi + 1) if on else range(0, 1))
            for counts in itertools.product(*ranges):
                rows.append((counts, region_to_pattern[occupied]))
        rows.sort(key=lambda r: r[0])
        for i, (counts, pat) in enumerate(rows, start=1):
            instances.append({
                "id": f"I{i}", "present": _counts_str(M, counts),
                "counts": list(counts), "pattern": list(pat),
                "class": pattern_to_class[pat],
            })

    by_class = {}
    for occupied, pat in region_to_pattern.items():
        by_class.setdefault(pattern_to_class[pat], []).append(occupied)
    class_to_pattern = {i: p for p, i in pattern_to_class.items()}

    classes = []
    for idx in sorted(class_to_pattern):
        occ = sorted(by_class.get(idx, []), key=lambda o: [int(x) for x in o])
        members = ([i["present"] for i in instances if i["class"] == idx] if listed
                   else [_region_text(M, o) for o in occ])
        classes.append({
            "class": idx, "pattern": list(class_to_pattern[idx]),
            "members": members,
            "configurations": sum(_region_size(M, o) for o in occ),
            "regions": [_region_text(M, o) for o in occ],
        })

    # Statechart over the regions. A transition is a type appearing or disappearing
    # entirely, which is the only move that can change anything here.
    edges = set()
    label = {a["type"]: (a.get("label") or a["type"]) for a in spec["actors"]}
    for occupied, pat in region_to_pattern.items():
        src = pattern_to_class[pat]
        for k, t in enumerate(M.order):
            nxt = occupied[:k] + (not occupied[k],) + occupied[k + 1:]
            if nxt not in region_to_pattern:
                continue
            dst = pattern_to_class[region_to_pattern[nxt]]
            if dst == src:
                continue
            edges.add((src, f"{label[t]} joins" if nxt[k]
                       else f"last {label[t]} leaves", dst))

    return {
        "ok": True,
        "engine": "smt",
        "order": list(M.order),
        "stats": {
            "variables": len(n) + len(g),
            "clauses": len(C),
            "configurations": total,
            "sat_calls": smt_calls,
            "regions": len(regions),
            "instances": len(instances),
            "classes": len(classes),
            "enumerated": listed,
            "mode": "regions",
            "quantities": False,
        },
        "regions": regions,
        "instances": instances,
        "classes": classes,
        "statechart": {
            "initial": pattern_to_class.get(region_to_pattern.get(init)),
            "states": sorted(class_to_pattern),
            "patterns": {str(i): list(class_to_pattern[i]) for i in class_to_pattern},
            "edges": [[a, l, b] for (a, l, b) in sorted(edges)],
        },
    }


def available():
    try:
        _z3()
        return True
    except SmtUnavailable:
        return False


# ---------------------------------------------------------------------------
# The path taken when timing or capacity is present
# ---------------------------------------------------------------------------

def _result_from_counts(M, spec, z3, n, g, C, q, finish, counts_to_pattern, smt_calls):
    """Same result shape, but built from concrete count vectors.

    With capacity or a deadline in play the answer genuinely varies with the numbers,
    so there is nothing to collapse and the configurations are walked one by one.
    """
    init = tuple(M.actors[t][0] for t in M.order)
    pattern_to_class, seen, queue = {}, {init}, [init]
    while queue:
        node = queue.pop(0)
        pat = counts_to_pattern.get(node)
        if pat is None:
            continue
        if pat not in pattern_to_class:
            pattern_to_class[pat] = len(pattern_to_class) + 1
        for k in range(len(M.order)):
            for step in (1, -1):
                nxt = node[:k] + (node[k] + step,) + node[k + 1:]
                if nxt in counts_to_pattern and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    for pat in counts_to_pattern.values():
        if pat not in pattern_to_class:
            pattern_to_class[pat] = len(pattern_to_class) + 1

    rows = sorted(counts_to_pattern.items())
    instances = [{"id": f"I{i}", "present": _counts_str(M, counts),
                  "counts": list(counts), "pattern": list(pat),
                  "class": pattern_to_class[pat]}
                 for i, (counts, pat) in enumerate(rows, start=1)]

    class_to_pattern = {i: p for p, i in pattern_to_class.items()}
    classes = []
    for idx in sorted(class_to_pattern):
        members = [i["present"] for i in instances if i["class"] == idx]
        classes.append({"class": idx, "pattern": list(class_to_pattern[idx]),
                        "members": members, "configurations": len(members),
                        "regions": []})

    label = {a["type"]: (a.get("label") or a["type"]) for a in spec["actors"]}
    edges = set()
    for counts, pat in counts_to_pattern.items():
        src = pattern_to_class[pat]
        for k, t in enumerate(M.order):
            for step, word in ((1, "joins"), (-1, "leaves")):
                nxt = counts[:k] + (counts[k] + step,) + counts[k + 1:]
                if nxt not in counts_to_pattern:
                    continue
                dst = pattern_to_class[counts_to_pattern[nxt]]
                if dst != src:
                    pre = "last " if step == -1 and nxt[k] == 0 else ""
                    edges.add((src, f"{pre}{label[t]} {word}", dst))

    return {
        "ok": True, "engine": "smt", "order": list(M.order),
        "stats": {"variables": len(n) + len(g) + (len(finish) if finish else 0),
                  "clauses": len(C), "configurations": len(counts_to_pattern),
                  "sat_calls": smt_calls, "regions": 0,
                  "instances": len(instances), "classes": len(classes),
                  "enumerated": True, "mode": "counts", "quantities": True},
        "regions": [], "instances": instances, "classes": classes,
        "statechart": {
            "initial": pattern_to_class.get(counts_to_pattern.get(init)),
            "states": sorted(class_to_pattern),
            "patterns": {str(i): list(class_to_pattern[i]) for i in class_to_pattern},
            "edges": [[a, l, b] for (a, l, b) in sorted(edges)]},
    }


# ---------------------------------------------------------------------------
# Findings only the numbers make possible
# ---------------------------------------------------------------------------

def _to_float(v):
    """z3 optimum -> float, across the numeric shapes Optimize can hand back.

    It returns IntNumRef for an integral optimum, RatNumRef otherwise, and an
    infinity object when the objective is unbounded. Guessing one of those and
    swallowing the failure hides real results, which is exactly what happened the
    first time this was written.
    """
    if hasattr(v, "as_fraction"):            # RatNumRef
        return float(v.as_fraction())
    if hasattr(v, "as_long"):                # IntNumRef
        return float(v.as_long())
    if hasattr(v, "numerator_as_long"):
        return v.numerator_as_long() / v.denominator_as_long()
    return float(str(v))                     # raises on oo / epsilon, deliberately


def extra_findings(spec, result, goalshift_dir=None):
    """Capacity ceilings and deadline shortfalls, both computed by optimisation.

    These are not detected by walking configurations, they are solved for, so the
    numbers come back exact rather than as the largest case that happened to be tried.
    """
    if not result.get("ok") or not result.get("stats", {}).get("quantities"):
        return []
    z3 = _z3()
    M = _model(spec, goalshift_dir)
    q = quantities(spec)
    label = {a["type"]: (a.get("label") or a["type"]) for a in spec["actors"]}
    glabel = {g["name"]: (g.get("label") or g["name"]) for g in spec["goals"]}
    out = []

    # ---- capacity ceilings -------------------------------------------------
    # How many of the depending type can the providers actually carry? Ask for the
    # largest count at which everything still holds.
    # Built without deadlines on purpose. A capacity ceiling and a missed deadline are
    # separate problems and an engineer fixes them separately, so an unmeetable
    # deadline must not make the ceiling query unsatisfiable and hide it.
    n, g, C, _q, _f = build(M, spec, include_deadlines=False)
    for dg, pg, _mult in M.deps:
        w = q["demand"].get((dg, pg))
        cap = q["capacity"].get(M.owner[pg])
        if w is None or cap is None:
            continue
        D, P = M.owner[dg], M.owner[pg]
        opt = z3.Optimize()
        opt.add(*C)
        for t in M.order:
            opt.add(g[M.root[t]] == (n[t] >= 1))     # everything present is satisfied
        best = opt.maximize(n[D])
        if opt.check() != z3.sat:
            continue
        try:
            ceiling = int(_to_float(best.value()))
        except (ValueError, AttributeError, TypeError):
            continue                          # unbounded, so no ceiling to report
        hi_D = M.actors[D][1]
        if ceiling < hi_D:
            out.append({
                "kind": "capacity-limit", "actor": D,
                "headline": (f"{label[D]} is capped at {ceiling} by "
                             f"{label[P]} capacity, not by its own bound of {hi_D}"),
                "ceiling": ceiling, "declared_max": hi_D,
                "provider": label[P], "capacity": cap, "demand": w,
                "goal": glabel.get(dg, dg), "provides": glabel.get(pg, pg),
                # The ceiling is only as real as the edge it is measured across,
                # so `analyze.provenance` gets the name of that edge.
                "dep": f"{dg} -> {pg}",
            })

    # ---- deadlines ---------------------------------------------------------
    # Compare the best achievable finish against the stated limit. Building without
    # the deadline is what lets the shortfall be measured rather than just detected.
    if q["deadline"]:
        n2, g2, C2, _q2, finish2 = build(M, spec, include_deadlines=False)
        for t, limit in q["deadline"].items():
            root = M.root.get(t)
            if not root or finish2 is None:
                continue
            opt = z3.Optimize()
            opt.add(*C2)
            opt.add(g2[root], n2[t] >= 1)
            best = opt.minimize(finish2[root])
            if opt.check() != z3.sat:
                out.append({
                    "kind": "deadline-unreachable", "actor": t,
                    "headline": f"{label[t]} cannot satisfy its root goal at all",
                    "deadline": limit})
                continue
            try:
                soonest = _to_float(best.value())
            except (ValueError, AttributeError, TypeError):
                continue
            if soonest > limit + 1e-9:
                out.append({
                    "kind": "deadline-miss", "actor": t,
                    "headline": (f"{label[t]} cannot meet its {limit:g} deadline. "
                                 f"The soonest it can finish is {soonest:g}"),
                    "deadline": limit, "soonest": soonest,
                    "shortfall": soonest - limit})
    return out
