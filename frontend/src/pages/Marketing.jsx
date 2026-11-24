import { useRef, useState } from 'react'
import {
  DemoPlayer,
  FindingArticle,
  FindingDetails,
  NavLink,
  PageHero,
  StepChip,
} from '../components.jsx'

function ContactForm() {
  const nameRef = useRef(null)
  const emailRef = useRef(null)
  const messageRef = useRef(null)
  const okRef = useRef(null)
  const [emailError, setEmailError] = useState(false)
  const [sent, setSent] = useState(false)

  const submit = (event) => {
    event.preventDefault()
    setEmailError(false)
    setSent(false)
    const email = emailRef.current?.value.trim() || ''
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError(true)
      emailRef.current?.focus()
      return
    }
    const name = nameRef.current?.value.trim() || ''
    const message = messageRef.current?.value.trim() || ''
    if (!name || message.length < 10) return
    setSent(true)
    window.requestAnimationFrame(() => {
      okRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }

  return (
    <form className="card" onSubmit={submit} noValidate>
      <div ref={okRef} className={`alert alert-ok${sent ? ' show' : ''}`} role="status" aria-live="polite">
        Looks good. In production this sends from the server. This preview does not send it.
      </div>
      <div className="fieldf">
        <label htmlFor="cName">Name</label>
        <input className="input" id="cName" ref={nameRef} required />
      </div>
      <div className="fieldf">
        <label htmlFor="cEmail">Email</label>
        <input className="input" id="cEmail" ref={emailRef} type="email" required />
        <div className={`err${emailError ? ' show' : ''}`} role="alert">Enter a valid email.</div>
      </div>
      <div className="fieldf">
        <label htmlFor="cCo">Company</label>
        <input className="input" id="cCo" />
      </div>
      <div className="fieldf">
        <label htmlFor="cMsg">Message</label>
        <textarea id="cMsg" ref={messageRef} required />
      </div>
      <button className="btn btn-primary btn-lg" type="submit">Send</button>
    </form>
  )
}

export function HomePage() {
  return (
    <>
      <section className="hero">
        <div className="wrap-wide hero-grid">
          <div className="reveal in">
            <div className="eyebrow">Requirements analysis</div>
            <h1>Your spec might be <span className="mark">missing something</span> important.</h1>
            <p className="lede">Upload a spec. We flag what is missing and check which setups can work.</p>
            <div className="hero-actions">
              <NavLink to="signup" className="btn btn-primary btn-lg">
                Get a gap report <span className="arr">→</span>
              </NavLink>
              <NavLink to="how" className="btn btn-secondary btn-lg">Watch how it works</NavLink>
            </div>
            <div className="hero-points">
              <span className="point"><i aria-hidden="true" /> PDF or text</span>
              <span className="point"><i aria-hidden="true" /> Quote for every gap</span>
              <span className="point"><i aria-hidden="true" /> You approve the model</span>
            </div>
          </div>
          <div className="preview reveal in d1" aria-label="Animated preview of a gap report">
            <div className="preview-chrome">
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <div className="dots"><span /><span /><span /></div>
                <span className="file">batch mixer spec.pdf</span>
              </div>
              <span className="pill pill-synth"><span className="live-dot" /> Synthetic example</span>
            </div>
            <div className="flow">
              <span>Document</span><span className="flow-line" />
              <span>Model</span><span className="flow-line" />
              <span className="on">Gap report</span>
            </div>
            <div className="panes">
              <div className="pane">
                <div className="scanbeam" />
                <h4>Source</h4>
                <p className="doc"><span className="pg">p2</span>The vessel is rated for <span className="hl">normal process operation</span>.</p>
                <p className="doc"><span className="pg">p4</span>The impeller shall run during mixing.</p>
                <p className="doc"><span className="pg">p6</span><span className="hl b">Heating is available</span> to hold temperature.</p>
                <p className="doc"><span className="pg">p6</span>A level transmitter is fitted.</p>
                <p className="doc"><span className="pg">p9</span>See Appendix B for layout.</p>
              </div>
              <div className="pane">
                <h4>Model</h4>
                <div className="mrow"><span className="k">Vessel</span><span className="v">2000 L</span></div>
                <div className="mrow miss"><span className="k">Max pressure</span><span className="v">not stated</span></div>
                <div className="mrow miss"><span className="k">Impeller speed</span><span className="v">not stated</span></div>
                <div className="mrow prop"><span className="k">Ambient</span><span className="v">AI idea <span className="blink">|</span></span></div>
              </div>
              <div className="pane">
                <h4>Start here</h4>
                <div className="fmini">
                  <div className="t">Max vessel pressure missing</div>
                  <div className="m">Relief and interlocks cannot be checked yet.</div>
                  <div className="meta"><span className="pill pill-high">High</span><span className="pill pill-med">Not stated</span></div>
                </div>
                <div className="fmini med">
                  <div className="t">Heater and level rule unclear</div>
                  <div className="m">Dry fire protection is not written down.</div>
                  <div className="meta"><span className="pill pill-med">Medium</span><span className="pill pill-med">Unclear</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="ticker" aria-hidden="true">
          <div className="ticker-track">
            <span>Quantities <b>•</b> Limits <b>•</b> Dependencies <b>•</b> Units <b>•</b> Interlocks <b>•</b> Ranges <b>•</b> Evidence <b>•</b></span>
            <span>Quantities <b>•</b> Limits <b>•</b> Dependencies <b>•</b> Units <b>•</b> Interlocks <b>•</b> Ranges <b>•</b> Evidence <b>•</b></span>
          </div>
        </div>
      </section>

      <section className="block alt" id="product">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">The problem</div>
            <h2>Specs leave things out.</h2>
            <p>Numbers, limits and rules get skipped or implied. You usually find out late.</p>
          </div>
          <div className="grid4">
            <article className="card reveal"><div className="icon">◈</div><h3>Quantities</h3><p>Volumes, rates and times with no values.</p></article>
            <article className="card reveal d1"><div className="icon amber">↕</div><h3>Limits</h3><p>Max and min values a design needs to start.</p></article>
            <article className="card reveal d2"><div className="icon violet">◎</div><h3>Dependencies</h3><p>What must be true before something can run.</p></article>
            <article className="card reveal d3"><div className="icon red">?</div><h3>Vague wording</h3><p>Phrases like normal operation, with nothing to check.</p></article>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">Two steps</div>
            <h2>Find gaps. Check what works.</h2>
            <p>We do not claim a spec is correct. We show what is missing, then test setups against a model you approve.</p>
          </div>
          <article className="step reveal">
            <div>
              <div className="step-num">Step 01</div>
              <h3>Find the gaps</h3>
              <p>We read the doc, draft a model and compare it back to the source.</p>
              <ul><li>Read PDF or text</li><li>Draft the model</li><li>Report gaps with quotes</li></ul>
              <p style={{ marginTop: 14 }}><NavLink to="how">See the animated walkthrough →</NavLink></p>
            </div>
            <div className="mini">
              <div className="mini-bar"><span>Gap scan</span><span className="pill pill-synth">Synthetic</span></div>
              <div className="gm"><span className="pill pill-high">High</span><div><b>Max pressure not stated</b><p>. 2: rated for normal operation.</p></div></div>
              <div className="gm"><span className="pill pill-high">High</span><div><b>Impeller speed missing</b><p>. 4: runs during mixing. No rpm.</p></div></div>
              <div className="gm"><span className="pill pill-med">Med</span><div><b>Heater rule unclear</b><p>. 6: heating is available.</p></div></div>
              <div style={{ height: 6 }} />
            </div>
          </article>
          <article className="step reveal">
            <div>
              <div className="step-num">Step 02</div>
              <h3>Check what can work</h3>
              <p>You add the missing values. The solver tests setups and shows what works or gets blocked.</p>
              <ul><li>Add missing numbers</li><li>Pick an engine</li><li>See working and failing setups</li></ul>
            </div>
            <div className="mini">
              <div className="mini-bar"><span>Solver</span><span className="mono">GoalShift SAT</span></div>
              <table>
                <thead><tr><th>Setup</th><th>Heater</th><th>Result</th></tr></thead>
                <tbody>
                  <tr><td>Level 40%, 6 bar</td><td>On</td><td className="ok">Works</td></tr>
                  <tr><td>Level 20%, 6 bar</td><td>On</td><td className="fail">Blocked</td></tr>
                  <tr><td>Level 40%, 10 bar</td><td>Off</td><td className="fail">Over limit</td></tr>
                  <tr><td>Level 55%, 4 bar</td><td>On</td><td className="ok">Works</td></tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </section>

      <section className="block alt">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">Clear roles</div>
            <h2>AI drafts. You decide. Solver checks.</h2>
            <p>Every result is labelled. Guesses are never shown as facts.</p>
          </div>
          <div className="grid4">
            <article className="role reveal"><div className="tag" style={{ color: 'var(--violet)' }}>AI</div><h3>Extraction</h3><p>Drafts parts, values and rules from the doc.</p></article>
            <article className="role reveal d1"><div className="tag" style={{ color: 'var(--ink2)' }}>Audit</div><h3>Source check</h3><p>Compares the draft to the original text.</p></article>
            <article className="role reveal d2"><div className="tag" style={{ color: 'var(--forest)' }}>Engineer</div><h3>Your review</h3><p>Accept, edit or reject. Then rerun.</p></article>
            <article className="role reveal d3"><div className="tag" style={{ color: 'var(--green)' }}>Solver</div><h3>Possibilities</h3><p>Tests setups against the model you approved.</p></article>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">Sample</div>
            <h2>Gaps, with evidence.</h2>
            <p>From a fictional mixer spec. For demo only.</p>
          </div>
          <div className="report reveal">
            <div className="report-bar">
              <div>
                <strong>Batch mixer control spec</strong>
                <div><span>Rev 0.3 · Synthetic example</span></div>
              </div>
              <NavLink to="sample" className="btn btn-secondary btn-sm">Open full sample</NavLink>
            </div>
            <div className="findings">
              <div className="label">Start here</div>
              <FindingArticle
                title="Max vessel pressure is missing"
                pill="High"
                pillClass="pill-high"
                body="No bound, no unit. Relief sizing cannot be checked."
                quote="The vessel is rated for normal process operation. p. 2"
                ask="What is the max pressure, and in what units?"
                askLabel="Ask the engineer"
              />
              <FindingArticle
                variant="med"
                title="Heater and level rule is unclear"
                pill="Medium"
                pillClass="pill-med"
                body="It may be assumed, but it is not written as a rule."
                quote="Heating is available to maintain batch temperature. p. 6"
                ask="Should heating stop below a set level?"
                askLabel="Ask the engineer"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="block alt">
        <div className="wrap sec-grid">
          <div className="reveal">
            <div className="eyebrow">Security</div>
            <h2 style={{ fontSize: 'clamp(1.65rem,3vw,2.1rem)' }}>Your spec stays private.</h2>
            <p style={{ color: 'var(--ink2)', marginTop: 10 }}>Docs belong to your account. No anonymous uploads. No public demo with your file.</p>
            <p style={{ marginTop: 14 }}><NavLink to="security">How docs are handled →</NavLink></p>
          </div>
          <ul className="seclist reveal d1">
            <li><span className="tick">✓</span>Private storage. Time limited download links.</li>
            <li><span className="tick">✓</span>AI runs on the server. Keys stay off the browser.</li>
            <li><span className="tick">✓</span>You can delete your docs.</li>
            <li><span className="tick">✓</span>No certification claims we cannot back up.</li>
          </ul>
        </div>
      </section>

      <section className="cta">
        <div className="wrap reveal">
          <h2>Find the gaps before you build.</h2>
          <p>Upload. Review the evidence. Fix the model. Run the checks.</p>
          <div className="actions">
            <NavLink to="signup" className="btn btn-white btn-lg">Get a gap report</NavLink>
            <NavLink to="how" className="btn btn-outline-w btn-lg">Watch the demos</NavLink>
          </div>
        </div>
      </section>
    </>
  )
}

export function HowPage() {
  const [paused, setPaused] = useState([false, false, false, false])
  const setDemoPaused = (index, value) => {
    setPaused((current) => current.map((item, i) => (i === index ? value : item)))
  }

  return (
    <>
      <div className="page-hero">
        <div className="wrap">
          <div className="eyebrow">How it works</div>
          <h1>From document to decisions.</h1>
          <p>Four stages. Each one is labelled. If we cannot check something, we say so. The clips below loop like GIFs. Pause or replay any of them.</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 18 }}>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => setPaused([true, true, true, true])}>
              Pause all demos
            </button>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => setPaused([false, false, false, false])}>
              Play all
            </button>
            <span className="pill pill-info" style={{ alignSelf: 'center' }}>All data below is synthetic</span>
          </div>
        </div>
      </div>
      <section className="block" style={{ paddingTop: 10 }}>
        <div className="wrap">
          <div className="demo-row reveal">
            <div className="demo-copy">
              <StepChip>Step 1 · Upload</StepChip>
              <h3>Drop in a file. We read it.</h3>
              <p>PDF or text first. DOCX and Markdown where supported. We check type and size before anything runs.</p>
              <ul><li>Readable text is pulled out</li><li>Bad files stop early</li><li>Pages stay linked to quotes</li></ul>
            </div>
            <DemoPlayer
              title="01 Upload and read"
              caption="Upload, progress, then readable pages."
              note="Synthetic file"
              paused={paused[0]}
              onToggle={(value) => setDemoPaused(0, value)}
            >
              <div className="drop seq1">
                <div className="bounce" style={{ fontSize: 22 }}>↓</div>
                <div className="filecard">
                  <div className="fileic">PDF</div>
                  <div style={{ flex: 1 }}>
                    <strong style={{ fontSize: 13 }}>mixer spec.pdf</strong>
                    <div style={{ fontSize: 11.5, color: 'var(--ink3)' }}>12 pages · 840 KB</div>
                    <div className="bar"><i /></div>
                  </div>
                </div>
                <span className="pill pill-ok seq3">Read ✓</span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--ink3)', marginTop: 10 }}>Drop file or click to browse</p>
              <div className="docbox seq2" style={{ marginTop: 12 }}>
                <strong style={{ fontSize: 12 }}>Text pulled out</strong>
                <div className="line" /><div className="line mid" /><div className="line short" />
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  <span className="pill pill-forest seq3">p. 2 linked</span>
                  <span className="pill pill-forest seq4">p. 4 linked</span>
                  <span className="pill pill-forest seq4">p. 6 linked</span>
                </div>
              </div>
            </DemoPlayer>
          </div>

          <div className="demo-row flip reveal">
            <div className="demo-copy">
              <StepChip>Step 2 · Find gaps</StepChip>
              <h3>We scan. Gaps pop out.</h3>
              <p>AI drafts parts, values and rules. An audit compares that draft to the source. Anything missing gets a quote and a page.</p>
              <ul><li>Not stated</li><li>Unclear</li><li>AI proposed, clearly marked</li></ul>
            </div>
            <DemoPlayer
              title="02 Scan and flag"
              caption="Scan line moves. Highlights and cards appear in order."
              note="Quotes included"
              paused={paused[1]}
              onToggle={(value) => setDemoPaused(1, value)}
            >
              <div className="two">
                <div className="docbox">
                  <div className="scanline" />
                  <strong style={{ fontSize: 12 }}>Source doc</strong>
                  <p className="doc" style={{ marginTop: 8 }}>Rated for <span className="hl seq2">normal operation</span>.</p>
                  <p className="doc">Impeller runs during mixing.</p>
                  <p className="doc"><span className="hl seq3">Heating is available</span>.</p>
                  <p className="doc">Level transmitter is fitted.</p>
                  <div className="line" /><div className="line short" />
                </div>
                <div>
                  <div className="fmini seq2">
                    <div className="t">Max pressure missing</div>
                    <div className="m">p. 2 · No value, no unit</div>
                    <div className="meta"><span className="pill pill-high">High</span></div>
                  </div>
                  <div className="fmini seq3" style={{ borderLeftColor: 'var(--amber)' }}>
                    <div className="t">Heater rule unclear</div>
                    <div className="m">p. 6 · No level limit stated</div>
                    <div className="meta"><span className="pill pill-med">Medium</span></div>
                  </div>
                  <div className="fmini seq4" style={{ borderLeftColor: 'var(--violet)' }}>
                    <div className="t">Ambient range</div>
                    <div className="m">AI proposed. Not in source.</div>
                    <div className="meta"><span className="pill pill-ai">AI idea</span></div>
                  </div>
                </div>
              </div>
            </DemoPlayer>
          </div>

          <div className="demo-row reveal">
            <div className="demo-copy">
              <StepChip>Step 3 · Review</StepChip>
              <h3>You fix the model.</h3>
              <p>Source on the left, model on the right. Type the missing value, accept it, rerun. No need to redo extraction.</p>
              <ul><li>Edit in place</li><li>Reject bad AI guesses</li><li>Rerun from your version</li></ul>
            </div>
            <DemoPlayer
              title="03 Review and edit"
              caption="Watch the value get typed, then accepted."
              note="You stay in control"
              paused={paused[2]}
              onToggle={(value) => setDemoPaused(2, value)}
            >
              <div className="two">
                <div className="docbox seq1">
                  <strong style={{ fontSize: 12 }}>Original · p. 6</strong>
                  <p style={{ fontSize: 13, color: 'var(--ink2)', marginTop: 8, lineHeight: 1.6 }}>
                    Heating is available to maintain batch temperature. A level transmitter is fitted on the vessel wall.
                  </p>
                  <span className="pill pill-synth" style={{ marginTop: 8 }}>Synthetic text</span>
                </div>
                <div>
                  <div className="fieldrow seq1">
                    <span style={{ color: 'var(--ink3)' }}>Max pressure</span>
                    <span><span className="typed">6 bar</span><span className="cursor" /></span>
                  </div>
                  <div className="fieldrow seq2"><span style={{ color: 'var(--ink3)' }}>Heater min level</span><strong>35%</strong></div>
                  <div className="fieldrow seq3"><span style={{ color: 'var(--ink3)' }}>Impeller speed</span><strong>120 to 480 rpm</strong></div>
                  <div className="seq4" style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                    <span className="btn btn-primary btn-sm" style={{ pointerEvents: 'none' }}>✓ Accepted</span>
                    <span className="btn btn-secondary btn-sm" style={{ pointerEvents: 'none' }}>Rerun</span>
                  </div>
                </div>
              </div>
              <div className="mini-stats seq4">
                <div className="stat"><b>3</b><span>Fixed</span></div>
                <div className="stat"><b>1</b><span>Rejected</span></div>
                <div className="stat"><b>0</b><span>Open</span></div>
              </div>
            </DemoPlayer>
          </div>

          <div className="demo-row flip reveal">
            <div className="demo-copy">
              <StepChip>Step 4 · Solver</StepChip>
              <h3>Now test what works.</h3>
              <p>Pick an engine. The solver checks setup after setup and stamps the result. Blocked parts are called out.</p>
              <ul><li>Engine name on every run</li><li>GoalShift SAT is the main engine</li><li>Z3 SMT only shows when set up and tested</li></ul>
            </div>
            <DemoPlayer
              title="04 Solver checks"
              caption="Rows are checked one by one, then counted."
              note="Result is only as good as your model"
              paused={paused[3]}
              onToggle={(value) => setDemoPaused(3, value)}
            >
              <div className="seq1" style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                <span className="mono">Engine: GoalShift SAT</span>
                <span style={{ fontSize: 12, color: 'var(--ink2)' }}><span className="spin" /> Checking setups</span>
              </div>
              <div className="docbox" style={{ padding: 0, overflow: 'hidden' }}>
                <table>
                  <thead><tr><th>Setup</th><th>Heater</th><th>Result</th></tr></thead>
                  <tbody>
                    <tr><td>Level 40%, 6 bar</td><td>On</td><td><span className="stamp work seq2">✓ Works</span></td></tr>
                    <tr><td>Level 20%, 6 bar</td><td>On</td><td><span className="stamp block seq3">Blocked</span></td></tr>
                    <tr><td>Level 40%, 10 bar</td><td>Off</td><td><span className="stamp block seq3">Over limit</span></td></tr>
                    <tr><td>Level 55%, 4 bar</td><td>On</td><td><span className="stamp work seq4">✓ Works</span></td></tr>
                  </tbody>
                </table>
              </div>
              <div className="mini-stats seq4">
                <div className="stat"><b style={{ color: 'var(--green)' }}>2</b><span>Working</span></div>
                <div className="stat"><b style={{ color: 'var(--red)' }}>2</b><span>Failing</span></div>
                <div className="stat"><b>1</b><span>Blocked part</span></div>
              </div>
              <p className="seq4" style={{ fontSize: 12.5, color: 'var(--ink2)', marginTop: 9 }}>Heater 1 is blocked when level is below 35%.</p>
            </DemoPlayer>
          </div>

          <p className="callout reveal">Solver output does not certify the original spec. It only checks the model you approved.</p>
          <div style={{ marginTop: 22, display: 'flex', gap: 10, flexWrap: 'wrap' }} className="reveal">
            <NavLink to="signup" className="btn btn-primary">Get a gap report</NavLink>
            <NavLink to="sample" className="btn btn-secondary">See a sample report</NavLink>
          </div>
        </div>
      </section>
    </>
  )
}

export function SamplePage() {
  return (
    <>
      <PageHero eyebrow="Sample report" title="A synthetic gap report.">
        <p>Fictional mixer spec. Not a customer doc. Not a real plant.</p>
      </PageHero>
      <div className="wrap report-layout">
        <aside className="side">
          <h3>Report</h3>
          <div className="meta"><span>Doc</span><strong>Synthetic</strong></div>
          <div className="meta"><span>Title</span><strong>Mixer spec</strong></div>
          <div className="meta"><span>Version</span><strong>Rev 0.3</strong></div>
          <div className="meta"><span>Method</span><strong>Extract, then audit</strong></div>
          <h3 style={{ marginTop: 16 }}>Types</h3>
          <div className="legend">
            <div><i style={{ background: 'var(--red)' }} />Not stated</div>
            <div><i style={{ background: 'var(--amber)' }} />Unclear</div>
            <div><i style={{ background: 'var(--violet)' }} />AI proposed</div>
            <div><i style={{ background: 'var(--green)' }} />Found in source</div>
            <div><i style={{ background: 'var(--ink3)' }} />Cannot analyse</div>
          </div>
        </aside>
        <div>
          <div className="banner">Synthetic example. Do not use this as a real safety or design check.</div>
          <div className="label">Start here</div>
          <FindingArticle
            title="Max vessel pressure is missing"
            pill="High"
            pillClass="pill-high"
            body="Relief and interlocks need a number and a unit."
            quote="The vessel is rated for normal process operation. p. 2"
            ask="What is the max pressure, and in what units?"
          />
          <FindingArticle
            title="Impeller speed is not given"
            pill="High"
            pillClass="pill-high"
            body="Run during mixing is not a speed range."
            quote="The impeller shall operate continuously during mixing. p. 4"
            ask="What rpm range is allowed?"
          />
          <FindingArticle
            variant="med"
            title="Heater and level rule is unclear"
            pill="Medium"
            pillClass="pill-med"
            body="Dry fire protection is not written as a rule."
            quote="Heating is available to maintain batch temperature. p. 6"
            ask="Should heating stop below a set level?"
          />
          <h2 style={{ fontSize: 18, margin: '24px 0 10px' }}>All findings</h2>
          <FindingDetails
            variant="ai"
            title="Ambient range was AI proposed"
            pill="AI idea"
            pillClass="pill-ai"
            body="5 to 40 C was drafted. It is not in the source."
            quote="No matching sentence in the source."
            ask="Confirm or replace this range."
          />
          <FindingDetails
            variant="none"
            title="Appendix B is missing"
            pill="Cannot analyse"
            pillClass="pill-info"
            body="Nozzle layout cannot be checked without it."
            quote="See Appendix B for nozzle layout. p. 9"
          />
          <FindingDetails
            variant="low"
            title="Vessel volume is stated"
            pill="In source"
            pillClass="pill-ok"
            body="2000 L is clear. Shown so gaps stand out."
            quote="The working volume is 2000 litres. p. 2"
          />
          <div className="card" style={{ marginTop: 18 }}>
            <h3 style={{ marginTop: 0 }}>Method and limits</h3>
            <p>AI drafts. Audit compares to source. No solver was run for this sample. This does not prove a spec is correct.</p>
          </div>
        </div>
      </div>
    </>
  )
}

export function SecurityPage() {
  return (
    <>
      <PageHero eyebrow="Security" title="What happens to your spec." wrapClassName="wrap prose">
        <p>Plain notes on handling. No certification claims.</p>
      </PageHero>
      <section className="block" style={{ paddingTop: 10 }}>
        <div className="wrap prose">
          <h2>Ownership</h2>
          <p>Docs sit under your account. Other accounts cannot see or run them.</p>
          <h2>Storage</h2>
          <p>Private storage. Downloads use short lived links. Traffic is encrypted in transit.</p>
          <h2>AI processing</h2>
          <p>Extraction runs on the server with the Anthropic API. Keys never go to the browser. Doc text is sent to that provider to do the work.</p>
          <h2>Logs</h2>
          <p>Error logs should not contain doc contents.</p>
          <h2>Deletion</h2>
          <p>You can delete docs you own. Linked analysis goes with them under the service rules.</p>
          <h2>What we do not claim</h2>
          <p>No GDPR, ISO or SOC claims here. Those need proof from the live system and legal review.</p>
        </div>
      </section>
    </>
  )
}

export function PricingPage() {
  return (
    <>
      <PageHero eyebrow="Pilot" title="Start with your own specs.">
        <p>A paid pilot on real docs. No made up prices or savings.</p>
      </PageHero>
      <section className="block" style={{ paddingTop: 12 }}>
        <div className="wrap" style={{ maxWidth: 680 }}>
          <article className="card" style={{ padding: 26 }}>
            <h3 style={{ fontSize: 21, marginTop: 0 }}>Pilot</h3>
            <p>For teams who want gap reports they can review and act on.</p>
            <ul className="check">
              <li>Private workspace</li>
              <li>Gap reports with quotes</li>
              <li>Model review and rerun</li>
              <li>Solver runs, engine labelled</li>
              <li>PDF export</li>
            </ul>
            <NavLink to="contact" className="btn btn-primary btn-lg">Request a pilot</NavLink>
          </article>
        </div>
      </section>
    </>
  )
}

export function AboutPage() {
  return (
    <>
      <PageHero eyebrow="About" title="ReqShift" wrapClassName="wrap prose">
        <p>Find the gaps before you build.</p>
      </PageHero>
      <section className="block" style={{ paddingTop: 10 }}>
        <div className="wrap prose">
          <p>Spec in. Gaps out. You supply answers. The solver checks what works.</p>
          <h2>What it is</h2>
          <p>A tool to find missing or unclear requirements early, then test setups against a model you approved.</p>
          <h2>What it is not</h2>
          <p>Not proof a spec is correct. Not a swap for engineering judgement.</p>
        </div>
      </section>
    </>
  )
}

export function ContactPage() {
  return (
    <>
      <PageHero eyebrow="Contact" title="Request a pilot.">
        <p>Short form. This preview checks it locally only.</p>
      </PageHero>
      <section className="block" style={{ paddingTop: 12 }}>
        <div className="wrap" style={{ maxWidth: 540 }}>
          <ContactForm />
        </div>
      </section>
    </>
  )
}

export function PrivacyPage() {
  return (
    <>
      <PageHero eyebrow="Legal" title="Privacy policy" wrapClassName="wrap prose">
        <p>Draft notes. Needs legal review.</p>
      </PageHero>
      <section className="block" style={{ paddingTop: 10 }}>
        <div className="wrap prose">
          <p>We process account details and docs you upload to run gap checks and solver jobs.</p>
          <h2>Docs</h2>
          <p>Stored privately under your account. Sent to the AI provider for extraction. You can delete them.</p>
          <h2>Account</h2>
          <p>Email and password, or Google sign in where set up. Reset and verify flows included.</p>
          <h2>Questions</h2>
          <p>Use the contact form.</p>
        </div>
      </section>
    </>
  )
}

export function TermsPage() {
  return (
    <>
      <PageHero eyebrow="Legal" title="Terms of use" wrapClassName="wrap prose">
        <p>Draft terms. Needs legal review.</p>
      </PageHero>
      <section className="block" style={{ paddingTop: 10 }}>
        <div className="wrap prose">
          <p>ReqShift drafts models, flags gaps with evidence and checks setups against a model you approve.</p>
          <h2>No correctness promise</h2>
          <p>Output does not prove a spec is correct, complete or safe. Engineers make the final calls.</p>
          <h2>Use</h2>
          <p>Only upload docs you have the right to process.</p>
        </div>
      </section>
    </>
  )
}
