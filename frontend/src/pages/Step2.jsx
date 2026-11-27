import { useMemo, useState } from 'react'
import { reanalyze } from '../api.js'

// Same limits app.py enforces (MAX_INSTANCES, MAX_CONFIGURATIONS). Checked here as
// well so a bad number is refused instantly instead of after a round trip.
const MAX_INSTANCES = 20
const MAX_CONFIGURATIONS = 20000

// Only a missing COUNT can be answered by typing a number. Capacity and timing gaps
// need a sentence in the document, so they are listed but get no inputs.
const answerable = (gap) => (gap.kind || 'cardinality') === 'cardinality'

const severityPill = {
  critical: 'pill-high',
  high: 'pill-med',
}

/**
 * Step 2 of the two-step flow. Step 1 lists the quantities the document never
 * states. Here the reader supplies them and /api/reanalyze re-proves the SAME model
 * with those bounds. No language model is called, so it answers in seconds.
 */
export default function Step2({ job, proof, onProved, onReset }) {
  const [draft, setDraft] = useState({})
  const [bad, setBad] = useState({})
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)

  const spec = job.spec
  const actors = useMemo(
    () => Object.fromEntries((spec?.actors || []).map((a) => [a.type, a])),
    [spec],
  )

  // One row per actor. The gap list can mention the same actor more than once.
  const askable = useMemo(() => {
    const seen = new Set()
    return (job.gaps || []).filter((g) => {
      if (!answerable(g) || !actors[g.actor] || seen.has(g.actor)) return false
      seen.add(g.actor)
      return true
    })
  }, [job.gaps, actors])
  const otherGaps = (job.gaps || []).filter((g) => !answerable(g))

  if (!spec || (!askable.length && !otherGaps.length)) return null

  const filled = Object.entries(draft).filter(
    ([, v]) => String(v.lo ?? '').trim() !== '' || String(v.hi ?? '').trim() !== '',
  )

  const setField = (type, key, value) => {
    setDraft((d) => ({ ...d, [type]: { ...(d[type] || {}), [key]: value } }))
    setBad((b) => ({ ...b, [type]: false }))
    setError('')
  }

  const submit = async () => {
    const clean = {}
    const marks = {}
    let problem = ''
    for (const [type, v] of filled) {
      const lo = String(v.lo ?? '').trim() === '' ? 0 : Number(v.lo)
      const hi = String(v.hi ?? '').trim() === '' ? lo : Number(v.hi)
      const label = actors[type]?.label || type
      if (!Number.isInteger(lo) || !Number.isInteger(hi) || lo < 0) {
        marks[type] = true
        problem ||= 'Counts must be whole numbers, zero or more.'
      } else if (hi < lo) {
        marks[type] = true
        problem ||= `The most ${label} cannot be fewer than the fewest.`
      } else if (hi > MAX_INSTANCES) {
        marks[type] = true
        problem ||= `${label} at ${hi} is more than GoalShift can enumerate. It reasons about every instance separately, so give the range you actually care about.`
      } else {
        clean[type] = { lo, hi }
      }
    }
    if (problem) {
      setBad(marks)
      setError(problem)
      return
    }

    let space = 1
    for (const a of spec.actors) {
      const v = clean[a.type] || { lo: a.lo, hi: a.hi }
      space *= Math.max(0, v.hi - v.lo) + 1
    }
    if (space > MAX_CONFIGURATIONS) {
      setError(`Those numbers describe ${space.toLocaleString()} configurations, too many to enumerate one at a time. Narrow the widest range and try again.`)
      return
    }

    // Always start from the document's own model, so answering twice does not
    // stack one set of answers on top of another.
    const next = JSON.parse(JSON.stringify(spec))
    next.actors.forEach((a) => {
      const v = clean[a.type]
      if (!v) return
      a.lo = v.lo
      a.hi = v.hi
      // Stated now, by the person who knows. This also lifts the "unconfirmed"
      // mark from findings that rested on the missing number.
      a.hi_stated = true
      a.hi_supplied = true
      a.lo_stated = true
      a.lo_supplied = true
      delete a.hi_unknown
    })

    setRunning(true)
    setError('')
    try {
      const r = await reanalyze({
        spec: next,
        trace: job.trace || {},
        engine: job.engine || 'sat',
        supplied: clean,
      })
      if (r.state === 'error') {
        setError((r.errors || ['That did not work.']).join(' '))
        return
      }
      onProved({ ...r, spec: next, supplied: clean })
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const range = (a) => `${a.lo ?? 0}..${a.hi ?? 1}`

  return (
    <div className="result-block step2">
      <div className="step2-head">
        <span className="pill pill-forest">Step 2</span>
        <h2>Supply what the document leaves out</h2>
      </div>
      <p className="muted">
        Give the fewest and most of each participant the system can have at once.
        Nothing is sent to the AI. The solver re-proves the same model with your
        numbers, usually in seconds. Leave a row blank and it stays an open gap.
      </p>

      {proof && (
        <div className="alert alert-ok show" role="status">
          Proved from {Object.keys(proof.supplied).length} number
          {Object.keys(proof.supplied).length === 1 ? '' : 's'} you supplied. The report
          above now reflects them.{' '}
          <button type="button" className="linkish" onClick={onReset}>
            Back to the document&apos;s numbers
          </button>
        </div>
      )}
      {error && <div className="alert alert-bad show" role="alert">{error}</div>}

      {askable.length > 0 && (
        <ul className="step2-list">
          {askable.map((g) => {
            const a = actors[g.actor]
            const v = draft[g.actor] || {}
            return (
              <li key={g.actor} className={`step2-row${bad[g.actor] ? ' bad' : ''}`}>
                <div className="step2-text">
                  <span className={`pill ${severityPill[g.severity] || 'pill-info'}`}>{g.severity}</span>
                  <strong>{g.label || g.actor}</strong>
                  <small>
                    {g.question}{' '}
                    {a.hi_unknown
                      ? `The analysis is standing in ${range(a)} because the document gives nothing.`
                      : `The analysis currently uses ${range(a)}.`}
                  </small>
                </div>
                <label className="step2-num">
                  <span>Fewest</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    step="1"
                    placeholder={String(a.lo ?? 0)}
                    value={v.lo ?? ''}
                    aria-label={`Fewest number of ${g.label || g.actor}`}
                    onChange={(e) => setField(g.actor, 'lo', e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && filled.length && !running) submit() }}
                  />
                </label>
                <label className="step2-num">
                  <span>Most</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    step="1"
                    placeholder={a.hi_unknown ? 'not stated' : String(a.hi ?? 1)}
                    value={v.hi ?? ''}
                    aria-label={`Most number of ${g.label || g.actor}`}
                    onChange={(e) => setField(g.actor, 'hi', e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && filled.length && !running) submit() }}
                  />
                </label>
              </li>
            )
          })}
        </ul>
      )}

      {otherGaps.length > 0 && (
        <details className="step2-other">
          <summary>
            {otherGaps.length} gap{otherGaps.length === 1 ? '' : 's'} a number here cannot answer
          </summary>
          <ul>
            {otherGaps.map((g, i) => (
              <li key={`${g.actor}-${g.kind}-${i}`}>
                <strong>{g.label || g.actor}.</strong> {g.to_decide}
              </li>
            ))}
          </ul>
        </details>
      )}

      {askable.length > 0 && (
        <div className="workspace-actions">
          <button
            className="btn btn-primary"
            type="button"
            disabled={!filled.length || running}
            onClick={submit}
          >
            {running ? 'Proving…' : 'Run proof analysis'}
          </button>
          <span className="hint">
            {filled.length
              ? `${filled.length} of ${askable.length} filled in.`
              : 'Fill in at least one row above.'}
          </span>
        </div>
      )}
    </div>
  )
}
