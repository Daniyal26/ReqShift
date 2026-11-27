import { useCallback, useEffect, useState } from 'react'
import { PageHero } from '../components.jsx'
import { useNavigation } from '../navigation.js'
import {
  getBackends,
  getExample,
  getExamples,
  getJob,
  readPdf,
  saveReport,
  startAnalysis,
} from '../api.js'

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || '').split(',')[1] || '')
    reader.onerror = () => reject(new Error('That file could not be read.'))
    reader.readAsDataURL(file)
  })
}

function short(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function LiveExampleStrip() {
  const [examples, setExamples] = useState([])
  const [error, setError] = useState('')
  const { navigate } = useNavigation()

  useEffect(() => {
    let alive = true
    getExamples()
      .then((data) => { if (alive) setExamples((data.examples || []).slice(0, 3)) })
      .catch((err) => { if (alive) setError(err.message) })
    return () => { alive = false }
  }, [])

  if (error) {
    return <div className="live-examples alert alert-bad show">Backend unavailable: {error}</div>
  }

  return (
    <div className="live-examples">
      {examples.length === 0 && <div className="card">Loading real examples from the backend…</div>}
      {examples.map((item) => (
        <button
          key={item.name}
          className="live-example card"
          type="button"
          onClick={() => navigate('analyze', { example: item.name })}
        >
          <span className="pill pill-forest">{item.words.toLocaleString()} words</span>
          <strong>{item.title}</strong>
          <small>{item.subtitle}</small>
          <span className="arr">Open in workspace →</span>
        </button>
      ))}
    </div>
  )
}

export default function AnalyzePage({ section }) {
  const [backends, setBackends] = useState(null)
  const [examples, setExamples] = useState([])
  const [mode, setMode] = useState('example')
  const [exampleName, setExampleName] = useState('')
  const [text, setText] = useState('')
  const [intake, setIntake] = useState(null)
  const [engine, setEngine] = useState('sat')
  const [gapsOnly, setGapsOnly] = useState(true)
  const [screen, setScreen] = useState(true)
  const [verify, setVerify] = useState(true)
  const [explain, setExplain] = useState(false)
  const [job, setJob] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saved, setSaved] = useState('')
  const [startedAt, setStartedAt] = useState(null)
  const [seconds, setSeconds] = useState(0)

  const loadExample = useCallback(async (name) => {
    if (!name) return
    setError('')
    setNotice('')
    setSaved('')
    setIntake(null)
    try {
      const data = await getExample(name)
      setText(data.text || '')
      setMode('example')
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    let alive = true
    getBackends()
      .then((data) => {
        if (!alive) return
        setBackends(data)
        if (data.smt === false) setEngine((value) => (value === 'smt' ? 'sat' : value))
      })
      .catch((err) => { if (alive) setError(err.message) })
    getExamples()
      .then((data) => { if (alive) setExamples(data.examples || []) })
      .catch((err) => { if (alive) setError(err.message) })
    return () => { alive = false }
  }, [])

  useEffect(() => {
    if (!section?.example) return
    setExampleName(section.example)
    loadExample(section.example)
  }, [section?.example, loadExample])

  useEffect(() => {
    if (!job?.id || job.state !== 'running') return undefined
    let cancelled = false
    const poll = async () => {
      try {
        const next = await getJob(job.id)
        if (!cancelled) setJob(next)
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          setBusy(false)
        }
      }
    }
    poll()
    const timer = window.setInterval(poll, 900)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [job?.id, job?.state])

  useEffect(() => {
    if (job && job.state !== 'running') setBusy(false)
  }, [job?.state])

  useEffect(() => {
    if (!busy || !startedAt) return undefined
    const timer = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [busy, startedAt])

  const loadFile = async (file) => {
    setError('')
    setNotice('')
    setSaved('')
    setIntake(null)
    if (!file) return
    if (/\.(docx?|xlsx?|pptx?)$/i.test(file.name)) {
      setError('That format cannot be read yet. Save it as PDF or paste the text.')
      return
    }
    if (/\.pdf$/i.test(file.name)) {
      if (file.size > 25 * 1024 * 1024) {
        setError('That PDF is larger than 25 MB.')
        return
      }
      try {
        const data = await fileToBase64(file)
        const result = await readPdf(file.name, data)
        setText(result.text || '')
        setIntake(result)
        setMode('paste')
        setNotice(`${result.name} read: ${result.pages} pages, ${result.words.toLocaleString()} words. Check the text before running it.`)
      } catch (err) {
        setError(err.message)
      }
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('That file is larger than 2 MB. Paste the relevant pages instead.')
      return
    }
    try {
      const content = await file.text()
      setText(content)
      setMode('paste')
      setNotice(`Loaded ${file.name}. Check the text before running it.`)
    } catch {
      setError('That file could not be read.')
    }
  }

  const run = async (overrides = {}) => {
    if (!text.trim()) {
      setError('Load an example, upload a document, or paste requirements first.')
      return
    }
    setError('')
    setNotice('')
    setSaved('')
    setJob(null)
    setBusy(true)
    setStartedAt(Date.now())
    setSeconds(0)
    try {
      const started = await startAnalysis({
        text: text.trim(),
        engine,
        gaps_only: gapsOnly,
        screen: overrides.screen === undefined ? screen : overrides.screen,
        verify,
        explain,
      })
      setJob({ id: started.id, state: 'running', stage: 'read', stages: [] })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const stopWatching = () => {
    setJob(null)
    setBusy(false)
    setNotice('Stopped watching. The server job may still finish.')
  }

  const save = async () => {
    if (!job) return
    setError('')
    try {
      const result = await saveReport({
        spec: job.spec,
        trace: job.trace,
        markdown: job.markdown || job.gaps_markdown || '',
      })
      setSaved(result.saved)
    } catch (err) {
      setError(err.message)
    }
  }

  const stages = job?.stages || []
  // A finished job reports stage "done", which is not in the list, so without this
  // every step loses its tick the moment the run succeeds.
  const finished = job?.state === 'done' || job?.state === 'gaps_only'
  const currentStage = finished
    ? stages.length
    : stages.findIndex((item) => item.id === job?.stage)
  const backendName = backends?.backends?.[0] || ''
  const markdown = job?.markdown || job?.gaps_markdown || ''
  const summary = Object.entries(job?.summary || {}).slice(0, 8)

  return (
    <>
      <PageHero eyebrow="Live workspace" title={<>Run a <em className="serif">real</em> gap analysis.</>}>
        <p>No account, no demo data in this flow. It calls the ReqShift backend, polls the real job, and shows what the server returns.</p>
        <div className="workspace-status">
          <span className={`pill ${backendName ? 'pill-ok' : 'pill-synth'}`}>
            <span className="live-dot" /> {backendName ? `Extractor: ${backendName}` : 'No extractor configured'}
          </span>
          <span className="pill pill-info">Engine: {engine === 'smt' ? 'z3 SMT' : 'GoalShift SAT'}</span>
        </div>
      </PageHero>

      <section className="block workspace-block" style={{ paddingTop: 12 }}>
        <div className="wrap workspace-grid">
          <div className="workspace-controls card">
            <h2>Requirements</h2>
            {!backendName && (
              <div className="alert alert-bad show">
                Authenticate the CLI or set ANTHROPIC_API_KEY on the backend. Uploads will work, but extraction cannot start without it.
              </div>
            )}
            {error && <div className="alert alert-bad show" role="alert">{error}</div>}
            {notice && <div className="alert alert-ok show" role="status">{notice}</div>}

            <div className="mode-tabs" role="tablist" aria-label="Input mode">
              <button type="button" className={mode === 'example' ? 'active' : ''} onClick={() => setMode('example')}>Example</button>
              <button type="button" className={mode === 'paste' ? 'active' : ''} onClick={() => setMode('paste')}>Paste text</button>
              <button type="button" className={mode === 'file' ? 'active' : ''} onClick={() => setMode('file')}>PDF / text</button>
            </div>

            {mode === 'example' && (
              <div className="fieldf">
                <label htmlFor="examplePick">Real example document</label>
                <select
                  className="input"
                  id="examplePick"
                  value={exampleName}
                  onChange={(event) => {
                    setExampleName(event.target.value)
                    loadExample(event.target.value)
                  }}
                >
                  <option value="">Choose an example…</option>
                  {examples.map((item) => (
                    <option key={item.name} value={item.name}>
                      {item.title} · {item.words.toLocaleString()} words
                    </option>
                  ))}
                </select>
              </div>
            )}

            {mode === 'file' && (
              <div className="fieldf">
                <label htmlFor="specFile">Specification file</label>
                <input
                  className="input"
                  id="specFile"
                  type="file"
                  accept=".pdf,.txt,.md"
                  onChange={(event) => {
                    loadFile(event.target.files?.[0])
                    event.target.value = ''
                  }}
                />
                <small className="hint">PDFs are read by the backend. Text and Markdown are read in the browser. 25 MB PDF limit, 2 MB text limit.</small>
              </div>
            )}

            {(mode === 'paste' || mode === 'example') && (
              <div className="fieldf">
                <label htmlFor="specText">Requirements text</label>
                <textarea
                  className="input spec-text"
                  id="specText"
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  rows={11}
                  placeholder="Paste the requirements you want checked…"
                />
                <small className="hint">{text.trim() ? `${text.trim().split(/\s+/).length.toLocaleString()} words loaded` : 'Nothing loaded yet'}</small>
              </div>
            )}

            {intake && (
              <div className="intake">
                <b>{intake.name}</b> · {intake.pages} pages · {intake.words.toLocaleString()} words
                {(intake.notes || []).length > 0 && (
                  <ul>
                    {intake.notes.map((note) => <li key={note}>{note}</li>)}
                  </ul>
                )}
              </div>
            )}

            <div className="workspace-options">
              <label className="checkline">
                <input type="checkbox" checked={gapsOnly} onChange={(event) => setGapsOnly(event.target.checked)} />
                Gap report only
              </label>
              <label className="checkline">
                <input type="checkbox" checked={screen} onChange={(event) => setScreen(event.target.checked)} />
                Check scope first
              </label>
              <label className="checkline">
                <input type="checkbox" checked={verify} onChange={(event) => setVerify(event.target.checked)} />
                Audit the model
              </label>
              <label className="checkline">
                <input type="checkbox" checked={explain} onChange={(event) => setExplain(event.target.checked)} />
                Write findings up
              </label>
              <label className="checkline">
                Engine
                <select className="input" value={engine} onChange={(event) => setEngine(event.target.value)}>
                  <option value="sat">GoalShift SAT</option>
                  <option value="smt" disabled={backends?.smt === false}>z3 SMT</option>
                </select>
              </label>
            </div>

            <div className="workspace-actions">
              <button className="btn btn-primary btn-lg" type="button" onClick={() => run()} disabled={busy || !text.trim()}>
                {busy ? 'Running…' : 'Run analysis'}
              </button>
              {busy && <button className="btn btn-secondary btn-lg" type="button" onClick={stopWatching}>Stop watching</button>}
            </div>
          </div>

          <div className="workspace-output card">
            {!job && !busy && (
              <div className="empty-run">
                <div className="empty-icon">◎</div>
                <h2>Ready when you are.</h2>
                <p>Load a real example or your own text, then run it. Progress, findings and the report come from the backend.</p>
              </div>
            )}

            {busy && !job?.id && (
              <div className="empty-run">
                <div className="spin" />
                <h2>Starting the job…</h2>
              </div>
            )}

            {job && (
              <>
                <div className="run-head">
                  <span className={`pill ${job.state === 'running' ? 'pill-info' : job.state === 'done' || job.state === 'gaps_only' ? 'pill-ok' : 'pill-high'}`}>
                    {job.state === 'gaps_only' ? 'Gaps ready' : job.state}
                  </span>
                  <span className="mono">#{job.id}</span>
                  <span className="mono">{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</span>
                </div>

                {stages.length > 0 && (
                  <ol className="run-stages">
                    {stages.map((item, index) => (
                      <li
                        key={item.id}
                        className={index < currentStage ? 'past' : index === currentStage ? 'now' : ''}
                      >
                        <span className="bead">{index < currentStage ? '✓' : index + 1}</span>
                        <span>{item.label}</span>
                      </li>
                    ))}
                  </ol>
                )}

                {job.state === 'out_of_scope' && (
                  <div className="result-block">
                    <h2>Out of scope</h2>
                    <p>{job.reason || 'The scope check stopped this document.'}</p>
                    <p className="muted">Run extraction anyway if you want to see what the model finds.</p>
                    <button className="btn btn-secondary" type="button" onClick={() => run({ screen: false })}>Extract anyway</button>
                  </div>
                )}

                {job.state === 'error' && (
                  <div className="result-block">
                    <h2>That run did not finish</h2>
                    <ul className="error-list">
                      {(job.errors || [job.error || 'Unknown error']).map((item) => <li key={item}>{item}</li>)}
                    </ul>
                    {job.kept_model && <p className="muted">Recovered model: <span className="mono">{job.kept_model}</span></p>}
                  </div>
                )}

                {(job.state === 'done' || job.state === 'gaps_only') && (
                  <div className="result-block">
                    <h2>{job.state === 'gaps_only' ? 'Gap report' : 'Analysis report'}</h2>
                    <div className="workspace-stats">
                      <div className="stat"><b>{(job.gaps || []).length}</b><span>Gaps</span></div>
                      {job.state === 'done' && <div className="stat"><b>{(job.findings || []).length}</b><span>Findings</span></div>}
                      {job.engine && <div className="stat"><b>{job.engine === 'smt' ? 'z3' : 'SAT'}</b><span>Engine</span></div>}
                    </div>
                    {summary.length > 0 && (
                      <div className="summary-grid">
                        {summary.map(([key, value]) => (
                          <div key={key}><span>{key.replace(/_/g, ' ')}</span><b>{short(value)}</b></div>
                        ))}
                      </div>
                    )}
                    {markdown && <pre className="report-md">{markdown}</pre>}
                    <div className="workspace-actions">
                      <button className="btn btn-primary" type="button" onClick={save}>Save report on server</button>
                      {saved && <span className="saved mono">{saved}</span>}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>
    </>
  )
}
