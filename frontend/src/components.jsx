import { useEffect, useRef, useState } from 'react'
import { useNavigation } from './navigation.js'

export function Brand({ light = false }) {
  return (
    <span className="brand" style={light ? { color: '#fff' } : undefined}>
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
        <rect x="3.5" y="8" width="15" height="15" rx="3" fill="none" stroke="#1F5C42" strokeWidth="2" />
        <rect x="13.5" y="9" width="15" height="15" rx="3" fill="#1F5C42" />
      </svg>
      ReqShift
    </span>
  )
}

export function NavLink({ to, extra, className, children, ...props }) {
  const { route, navigate } = useNavigation()
  const { onClick, ...rest } = props

  return (
    <a
      {...rest}
      href={`#${to}`}
      className={className}
      aria-current={route === to ? 'page' : undefined}
      onClick={(event) => {
        if (onClick) onClick(event)
        if (event.defaultPrevented) return
        event.preventDefault()
        navigate(to, extra)
      }}
    >
      {children}
    </a>
  )
}

export function Header({ menuOpen, onToggleMenu, scrolled }) {
  return (
    <>
      <header className={`nav${scrolled ? ' scrolled' : ''}`} id="nav">
        <div className="wrap-wide nav-inner">
          <NavLink to="home" className="brand" aria-label="ReqShift home">
            <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
              <rect x="3.5" y="8" width="15" height="15" rx="3" fill="none" stroke="#1F5C42" strokeWidth="2" />
              <rect x="13.5" y="9" width="15" height="15" rx="3" fill="#1F5C42" />
            </svg>
            ReqShift
          </NavLink>
          <nav className="nav-links" aria-label="Primary">
            <NavLink to="home" extra="product">Product</NavLink>
            <NavLink to="how">How it works</NavLink>
            <NavLink to="analyze">Live analysis</NavLink>
            <NavLink to="security">Security</NavLink>
          </nav>
          <div className="nav-cta">
            <NavLink to="analyze" className="btn btn-ghost btn-sm">Examples</NavLink>
            <NavLink to="analyze" className="btn btn-primary btn-sm">Run analysis</NavLink>
            <button
              className="menu-btn"
              id="menuBtn"
              type="button"
              aria-label="Open menu"
              aria-expanded={menuOpen}
              aria-controls="mobileNav"
              onClick={onToggleMenu}
            >
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M3 5h12M3 9h12M3 13h12" />
              </svg>
            </button>
          </div>
        </div>
      </header>
      <div className={`mobile-nav${menuOpen ? ' open' : ''}`} id="mobileNav" hidden={!menuOpen}>
        <NavLink to="home">Product</NavLink>
        <NavLink to="how">How it works</NavLink>
        <NavLink to="analyze">Live analysis</NavLink>
        <NavLink to="security">Security</NavLink>
        <NavLink to="pricing">Pilot</NavLink>
        <NavLink to="about">About</NavLink>
        <div className="mcta">
          <NavLink to="analyze" className="btn btn-secondary btn-full">Browse examples</NavLink>
          <NavLink to="analyze" className="btn btn-primary btn-full">Run analysis</NavLink>
        </div>
      </div>
    </>
  )
}

export function Footer() {
  return (
    <footer>
      <div className="wrap-wide">
        <div className="foot">
          <div>
            <div className="brand" style={{ marginBottom: 9 }}>
              <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden="true">
                <rect x="3.5" y="8" width="15" height="15" rx="3" fill="none" stroke="#1F5C42" strokeWidth="2" />
                <rect x="13.5" y="9" width="15" height="15" rx="3" fill="#1F5C42" />
              </svg>
              ReqShift
            </div>
            <p>Find the gaps before you build.</p>
          </div>
          <div>
            <h4>Product</h4>
            <ul>
              <li><NavLink to="how">How it works</NavLink></li>
              <li><NavLink to="analyze">Live analysis</NavLink></li>
              <li><NavLink to="security">Security</NavLink></li>
              <li><NavLink to="pricing">Pilot</NavLink></li>
            </ul>
          </div>
          <div>
            <h4>Company</h4>
            <ul>
              <li><NavLink to="about">About</NavLink></li>
            </ul>
          </div>
          <div>
            <h4>Legal</h4>
            <ul>
              <li><NavLink to="privacy">Privacy policy</NavLink></li>
              <li><NavLink to="terms">Terms</NavLink></li>
            </ul>
          </div>
        </div>
        <div className="foot-b">
          <span>© {new Date().getFullYear()} ReqShift</span>
          <span>Spec in. Gaps out.</span>
        </div>
      </div>
    </footer>
  )
}

export function PageHero({ eyebrow, title, children, wrapClassName = 'wrap' }) {
  return (
    <div className="page-hero">
      <div className={wrapClassName}>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {children}
      </div>
    </div>
  )
}

export function StepChip({ children }) {
  return <span className="step-chip"><i aria-hidden="true" />{children}</span>
}

export function FindingArticle({ variant = '', title, pill, pillClass, body, quote, ask, askLabel = 'Ask' }) {
  return (
    <article className={`finding ${variant}`.trim()}>
      <div className="ftop">
        <h3>{title}</h3>
        <span className={`pill ${pillClass}`}>{pill}</span>
      </div>
      <p>{body}</p>
      <div className="quote">{quote}</div>
      <div className="q"><strong>{askLabel}</strong>{ask}</div>
    </article>
  )
}

export function FindingDetails({ variant = '', title, pill, pillClass, body, quote, ask, askLabel = 'Ask' }) {
  return (
    <details className={`finding ${variant}`.trim()}>
      <summary>
        <div className="ftop">
          <h3>{title}</h3>
          <span className={`pill ${pillClass}`}>{pill}</span>
        </div>
        <p>{body}</p>
        <div className="more">Show detail</div>
      </summary>
      <div className="quote">{quote}</div>
      {ask && <div className="q"><strong>{askLabel}</strong>{ask}</div>}
    </details>
  )
}

export function DemoPlayer({ title, caption, note, paused, onToggle, children }) {
  const stageRef = useRef(null)
  const [offscreen, setOffscreen] = useState(false)
  const [runKey, setRunKey] = useState(0)

  useEffect(() => {
    const stage = stageRef.current
    if (!stage || !('IntersectionObserver' in window)) return undefined
    const observer = new IntersectionObserver(
      ([entry]) => setOffscreen(!entry.isIntersecting),
      { threshold: 0.08 },
    )
    observer.observe(stage)
    return () => observer.disconnect()
  }, [runKey])

  const replay = () => {
    onToggle(false)
    setRunKey((value) => value + 1)
  }

  return (
    <div className="gif-wrap">
      <div className="gif-bar">
        <span className="ttl"><span className="live-dot" /> {title}</span>
        <div className="gif-controls">
          <button
            className="ctl"
            type="button"
            aria-pressed={paused}
            onClick={() => onToggle(!paused)}
          >
            {paused ? '▶ Play' : '❚❚ Pause'}
          </button>
          <button className="ctl" type="button" onClick={replay}>↺ Replay</button>
        </div>
      </div>
      <div
        key={runKey}
        ref={stageRef}
        className={`gif-stage gif-run${paused ? ' paused' : ''}${offscreen ? ' offscreen' : ''}`}
        data-gif
      >
        <span className="gif-badge">GIF DEMO · 8s LOOP</span>
        {children}
        <div className="gif-progress"><i /></div>
      </div>
      <div className="gif-cap">
        <span>{caption}</span>
        <span>{note}</span>
      </div>
    </div>
  )
}

export function ProductShowcase() {
  const sectionRef = useRef(null)
  const frameRef = useRef(null)
  const [frameWidth, setFrameWidth] = useState(1120)
  const [inView, setInView] = useState(true)

  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return undefined
    const update = () => setFrameWidth(frame.clientWidth || 1120)
    update()
    if (!('ResizeObserver' in window)) {
      window.addEventListener('resize', update)
      return () => window.removeEventListener('resize', update)
    }
    const observer = new ResizeObserver(update)
    observer.observe(frame)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const section = sectionRef.current
    if (!section || !('IntersectionObserver' in window)) return undefined
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.05 })
    observer.observe(section)
    return () => observer.disconnect()
  }, [])

  const mobile = frameWidth < 560
  const compact = frameWidth < 720
  const canvasWidth = compact ? 860 : 1120
  const scale = frameWidth / canvasWidth

  return (
    <section id="showcase" ref={sectionRef} className={`showcase${inView ? '' : ' paused'}`} aria-label="Animated ReqShift product preview">
      <div className="showcase-backdrop" aria-hidden="true" />
      <div className="showcase-frame" ref={frameRef} style={mobile ? undefined : { height: `${630 * scale}px` }}>
        {mobile ? (
          <div className="showcase-mobile" aria-hidden="true">
            <div className="showcase-mobile-head">
              <span className="showcase-mark" />
              <span><b>ReqShift</b><small>Synthetic workspace</small></span>
              <span className="showcase-export">Report</span>
            </div>
            <div className="showcase-mobile-title">Find the gaps, then check what works.</div>
            <div className="showcase-mobile-stats">
              <div><b>7</b><small>Gaps found</small></div>
              <div><b>12</b><small>Quotes linked</small></div>
              <div><b>16</b><small>Setups tried</small></div>
            </div>
            <div className="showcase-mobile-row high"><span>Max pressure missing</span><em>High</em></div>
            <div className="showcase-mobile-row med"><span>Heater rule unclear</span><em>Medium</em></div>
            <div className="showcase-mobile-row ai"><span>Ambient range proposed</span><em>Review</em></div>
          </div>
        ) : (
          <div
            className={`showcase-canvas showcase-run${compact ? ' compact' : ''}`}
            style={{ width: canvasWidth, transform: `scale(${scale})` }}
            aria-hidden="true"
          >
          <aside className="showcase-sidebar">
            <div className="showcase-brand"><span className="showcase-mark" />{!compact && <b>ReqShift</b>}</div>
            {!compact && (
              <div className="showcase-account">
                <span>Batch mixer spec</span>
                <small>Rev 0.3 · 12 pages</small>
              </div>
            )}
            <div className="showcase-nav">
              <span className="active"><i className="showcase-ico ico-home" />{!compact && 'Overview'}</span>
              <span><i className="showcase-ico ico-doc" />{!compact && 'Documents'}</span>
              <span><i className="showcase-ico ico-grid" />{!compact && 'Model'}</span>
              <span><i className="showcase-ico ico-check" />{!compact && 'Solver'}</span>
            </div>
            {!compact && <div className="showcase-sidefoot">Synthetic workspace</div>}
          </aside>
          <main className="showcase-main">
            <div className="showcase-topbar">
              <div className="showcase-crumb">Batch mixer spec <span>/</span> Overview</div>
              <div className="showcase-tools"><span className="showcase-search" /><span className="showcase-bell" /></div>
            </div>
            <div className="showcase-content">
              <div className="showcase-heading">
                <div>
                  <small>Requirement review</small>
                  <h3>Find the gaps, then check what works.</h3>
                </div>
                <span className="showcase-export">Export gap report</span>
              </div>
              <div className="showcase-stats">
                <div className="showcase-stat"><small>Gaps found</small><b>7</b><span className="showcase-trend">3 high</span></div>
                <div className="showcase-stat"><small>Quotes linked</small><b>12</b><span>Every finding traced</span></div>
                <div className="showcase-stat"><small>Model fields</small><b>24</b><span>18 approved</span></div>
                <div className="showcase-stat"><small>Setups tried</small><b>16</b><span className="showcase-meter"><i /></span></div>
              </div>
              <div className="showcase-lower">
                <div className="showcase-card">
                  <div className="showcase-cardhead"><b>Gaps with evidence</b><span>Source linked</span></div>
                  <div className="showcase-reportrow showcase-seq1">
                    <span className="showcase-spin" />
                    <span><b>Reading page 2</b><small>Checking vessel pressure wording</small></span>
                  </div>
                  <div className="showcase-reportrow showcase-seq2">
                    <span className="showcase-tick" />
                    <span><b>Max pressure missing</b><small>p. 2 · No value or unit</small></span>
                    <em className="high">High</em>
                  </div>
                  <div className="showcase-reportrow showcase-seq3">
                    <span className="showcase-tick" />
                    <span><b>Heater rule unclear</b><small>p. 6 · Level limit not stated</small></span>
                    <em className="med">Medium</em>
                  </div>
                  <div className="showcase-reportrow showcase-seq4">
                    <span className="showcase-tick ai" />
                    <span><b>Ambient range proposed</b><small>AI idea · Not in source</small></span>
                    <em className="review">Review</em>
                  </div>
                </div>
                <div className="showcase-side-col">
                  <div className="showcase-card">
                    <div className="showcase-cardhead"><b>Model</b><span>Engineer review</span></div>
                    <div className="showcase-field showcase-seq2"><span>Max pressure</span><b><span className="showcase-typed">6 bar</span><span className="showcase-cursor" /></b></div>
                    <div className="showcase-field showcase-seq3"><span>Heater min level</span><b>35%</b></div>
                    <div className="showcase-field showcase-seq4"><span>Impeller speed</span><b>120–480 rpm</b></div>
                  </div>
                  <div className="showcase-card">
                    <div className="showcase-cardhead"><b>Solver</b><span>GoalShift SAT</span></div>
                    <div className="showcase-solver">
                      <span className="showcase-ok">2 works</span>
                      <span className="showcase-bad">2 blocked</span>
                      <span>1 open gap</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="showcase-scan" />
            <div className="showcase-progress"><i /></div>
          </main>
          </div>
        )}
      </div>
      <div className="showcase-fade" aria-hidden="true" />
    </section>
  )
}
