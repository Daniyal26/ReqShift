import { useState } from 'react'
import { DemoPlayer, NavLink, PageHero, ProductShowcase, StepChip } from '../components.jsx'
import { LiveExampleStrip } from './Analyze.jsx'

export function HomePage() {
  return (
    <>
      <section className="hero">
        <div className="wrap-wide hero-grid">
          <div className="reveal in">
            <div className="eyebrow">A little clarity for messy specs</div>
            <h1>Find what the spec <em className="serif">never says.</em></h1>
            <p className="lede">ReqShift reads your requirements, drafts a model, and shows the gaps with evidence. No account needed.</p>
            <div className="hero-actions">
              <NavLink to="analyze" className="btn btn-primary btn-lg">
                Run a real analysis <span className="arr">→</span>
              </NavLink>
              <NavLink to="how" className="btn btn-text btn-lg">Watch how it works <span className="arr">→</span></NavLink>
            </div>
            <div className="hero-points">
              <span className="point"><i aria-hidden="true" /> PDF or text</span>
              <span className="point"><i aria-hidden="true" /> Quote for every gap</span>
              <span className="point"><i aria-hidden="true" /> You approve the model</span>
            </div>
          </div>
          <aside className="hero-evidence reveal in d1" aria-label="Synthetic gap report preview">
            <div className="evidence-top">
              <span className="evidence-dots" aria-hidden="true"><i /><i /><i /></span>
              <span className="evidence-file">batch mixer spec.pdf</span>
              <span className="pill pill-synth">Synthetic</span>
            </div>
            <div className="evidence-body">
              <div className="evidence-kicker">Gap report</div>
              <h2>What the document <em className="serif">never says.</em></h2>
              <div className="evidence-count">
                <strong>7</strong>
                <span>gaps found with<br />source quotes</span>
              </div>
              <div className="evidence-list">
                <div className="evidence-row">
                  <span className="evidence-index">01</span>
                  <span className="evidence-copy"><b>Max pressure missing</b><small>p. 2 · no value or unit</small></span>
                  <em>High</em>
                </div>
                <div className="evidence-row med">
                  <span className="evidence-index">02</span>
                  <span className="evidence-copy"><b>Heater rule unclear</b><small>p. 6 · level limit not stated</small></span>
                  <em>Medium</em>
                </div>
                <div className="evidence-row ai">
                  <span className="evidence-index">03</span>
                  <span className="evidence-copy"><b>Ambient range proposed</b><small>AI idea · not in source</small></span>
                  <em>Review</em>
                </div>
              </div>
            </div>
            <div className="evidence-foot"><span>AI drafts</span><span>Audit checks</span><span>Solver proves</span></div>
          </aside>
        </div>
      </section>

      <ProductShowcase />

      <section className="block alt" id="product">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">The problem</div>
            <h2>Specs leave <em className="serif">things out.</em></h2>
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
            <h2>Find gaps. <em className="serif">Check what works.</em></h2>
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
            <h2>AI drafts. <em className="serif">You decide.</em></h2>
            <p>Every result is labelled. Guesses are never shown as facts.</p>
          </div>
          <div className="feature-list">
            <article className="feature-row reveal">
              <span className="feature-num">01</span>
              <div><h3>Extraction</h3><p>Drafts parts, values and rules from the document.</p></div>
              <span className="feature-tag violet">AI</span>
            </article>
            <article className="feature-row reveal d1">
              <span className="feature-num">02</span>
              <div><h3>Source check</h3><p>Compares the draft back to the original text.</p></div>
              <span className="feature-tag">Audit</span>
            </article>
            <article className="feature-row reveal d2">
              <span className="feature-num">03</span>
              <div><h3>Your review</h3><p>Accept, edit or reject, then rerun without re-reading.</p></div>
              <span className="feature-tag forest">Engineer</span>
            </article>
            <article className="feature-row reveal d3">
              <span className="feature-num">04</span>
              <div><h3>Possibilities</h3><p>Tests setups against the model you approved.</p></div>
              <span className="feature-tag green">Solver</span>
            </article>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">Real examples</div>
            <h2>Start with a <em className="serif">real specification.</em></h2>
            <p>These files come from the backend. Pick one and it opens in the live workspace.</p>
          </div>
          <LiveExampleStrip />
        </div>
      </section>

      <section className="block alt">
        <div className="wrap privacy-grid">
          <div className="reveal">
            <div className="eyebrow">Private by design</div>
            <h2>Your spec stays <em className="serif">with the job.</em></h2>
            <p>No account is needed for this workspace. Jobs live in server memory and are written to disk only when you choose to save a report.</p>
            <p style={{ marginTop: 14 }}><NavLink to="security">Read the handling notes →</NavLink></p>
          </div>
          <div className="privacy-table reveal d1">
            <div><span>Your document</span><b>Read by your local backend</b></div>
            <div><span>AI credentials</span><b>Never sent to the browser</b></div>
            <div><span>Job results</span><b>Held in server memory</b></div>
            <div><span>Saved reports</span><b>Only when you press save</b></div>
            <div><span>Accounts</span><b>None needed</b></div>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          <div className="works-strip reveal">
            <span>PDF specifications</span>
            <span>Pasted requirements</span>
            <span>GoalShift SAT</span>
            <span>z3 SMT</span>
            <span>Local Python backend</span>
          </div>
        </div>
      </section>

      <section className="block alt">
        <div className="wrap faq-grid">
          <div className="reveal">
            <div className="eyebrow">Questions, answered.</div>
            <h2>The short <em className="serif">answers.</em></h2>
            <p>Plain answers about what this runs, what it saves, and what it can prove.</p>
          </div>
          <div className="faq-list reveal d1">
            <details>
              <summary>What is ReqShift?</summary>
              <p>A tool that reads requirements, drafts a model, and reports what the document never states.</p>
            </details>
            <details>
              <summary>Do I need an account?</summary>
              <p>No. The live workspace runs on the local backend without sign-in.</p>
            </details>
            <details>
              <summary>Does it prove my spec is safe?</summary>
              <p>No. It checks the model you approve. Engineers still make the final calls.</p>
            </details>
            <details>
              <summary>What gets saved?</summary>
              <p>Only what you explicitly save. Job results otherwise stay in server memory.</p>
            </details>
          </div>
        </div>
      </section>

      <section className="cta">
        <div className="wrap reveal">
          <h2>Your next spec, <em className="serif">already checked.</em></h2>
          <p>Upload. Review the evidence. Fix the model. Run the checks.</p>
          <div className="actions">
            <NavLink to="analyze" className="btn btn-white btn-lg">Run a gap report</NavLink>
            <NavLink to="how" className="btn btn-outline-w btn-lg">See how it works</NavLink>
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
          <h1>From document to <em className="serif">decisions.</em></h1>
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
            <NavLink to="analyze" className="btn btn-primary">Run a real analysis</NavLink>
            <NavLink to="analyze" className="btn btn-secondary">Browse real examples</NavLink>
          </div>
        </div>
      </section>
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
          <h2>Accounts</h2>
          <p>There is no sign-in in this workspace. The live analysis flow does not store user accounts.</p>
          <h2>Where the text goes</h2>
          <p>The browser sends requirement text to the local Python backend. PDFs are decoded there. Extraction credentials stay on the backend.</p>
          <h2>Job state</h2>
          <p>Running jobs live in server memory. Results stay there until the server restarts, unless you choose to save a report.</p>
          <h2>Saving</h2>
          <p>The save button writes the model, trace and report to the backend output folder. Nothing is saved without that action.</p>
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
              <li>Real gap reports from the backend</li>
              <li>Quotes from the source document</li>
              <li>Model review and rerun</li>
              <li>Solver runs, engine labelled</li>
              <li>Saved reports written on request</li>
            </ul>
            <NavLink to="analyze" className="btn btn-primary btn-lg">Open the workspace</NavLink>
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

export function PrivacyPage() {
  return (
    <>
      <PageHero eyebrow="Legal" title="Privacy policy" wrapClassName="wrap prose">
        <p>Draft notes. Needs legal review.</p>
      </PageHero>
      <section className="block" style={{ paddingTop: 10 }}>
        <div className="wrap prose">
          <p>The workspace processes the requirement text you choose to analyse. It does not ask for an account.</p>
          <h2>Documents</h2>
          <p>The text is sent to the local backend and, during extraction, to the configured AI provider. Job results are held in server memory.</p>
          <h2>Saved reports</h2>
          <p>Reports are written to the backend output folder only when you press the save button.</p>
          <h2>Accounts</h2>
          <p>No account, password, reset or email verification flow is part of this workspace.</p>
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
