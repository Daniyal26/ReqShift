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
            <NavLink to="sample">Sample report</NavLink>
            <NavLink to="security">Security</NavLink>
          </nav>
          <div className="nav-cta">
            <NavLink to="login" className="btn btn-ghost">Sign in</NavLink>
            <NavLink to="signup" className="btn btn-primary">Get a gap report</NavLink>
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
        <NavLink to="sample">Sample report</NavLink>
        <NavLink to="security">Security</NavLink>
        <NavLink to="pricing">Pilot</NavLink>
        <NavLink to="about">About</NavLink>
        <NavLink to="contact">Contact</NavLink>
        <div className="mcta">
          <NavLink to="login" className="btn btn-secondary btn-full">Sign in</NavLink>
          <NavLink to="signup" className="btn btn-primary btn-full">Get a gap report</NavLink>
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
              <li><NavLink to="sample">Sample report</NavLink></li>
              <li><NavLink to="security">Security</NavLink></li>
              <li><NavLink to="pricing">Pilot</NavLink></li>
            </ul>
          </div>
          <div>
            <h4>Company</h4>
            <ul>
              <li><NavLink to="about">About</NavLink></li>
              <li><NavLink to="contact">Contact</NavLink></li>
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

export function PasswordInput({ id, label, value, onChange }) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="fieldf">
      <label htmlFor={id}>{label}</label>
      <div className="pw">
        <input
          className="input"
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          required
        />
        <button
          className="pwt"
          type="button"
          aria-label={visible ? `Hide ${label}` : `Show ${label}`}
          onClick={() => setVisible((value) => !value)}
        >
          {visible ? 'Hide' : 'Show'}
        </button>
      </div>
    </div>
  )
}
