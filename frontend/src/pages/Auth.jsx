import { useEffect, useRef, useState } from 'react'
import { Brand, NavLink, PasswordInput } from '../components.jsx'
import { useNavigation } from '../navigation.js'

function validEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

function AuthAside({ title, copy, note }) {
  return (
    <aside className="aside">
      <div>
        <Brand light />
        <h2>{title}</h2>
        <p>{copy}</p>
      </div>
      <p style={{ fontSize: 12.5, opacity: 0.85 }}>{note}</p>
    </aside>
  )
}

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [alert, setAlert] = useState('')
  const [busy, setBusy] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  const submit = (event) => {
    event.preventDefault()
    setAlert('')
    if (!validEmail(email) || password.length < 8) {
      setAlert('Check your email and password. Password needs 8 or more characters.')
      return
    }
    setBusy(true)
    timerRef.current = window.setTimeout(() => {
      setBusy(false)
      setAlert('Sign in is not connected in this preview.')
    }, 650)
  }

  return (
    <div className="auth">
      <AuthAside
        title="Find gaps before you build."
        copy="AI drafts. You decide. Solver checks."
        note="Live sign in needs the auth service."
      />
      <div className="panel">
        <form className="acard" onSubmit={submit} noValidate>
          <h1>Sign in</h1>
          <p className="sub">Use your email and password.</p>
          <div className={`alert alert-err${alert ? ' show' : ''}`} role="alert">{alert}</div>
          <div className="fieldf">
            <label htmlFor="lEmail">Email</label>
            <input
              className="input"
              id="lEmail"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <PasswordInput
            id="lPass"
            label="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button className="btn btn-primary btn-full btn-lg" type="submit" disabled={busy}>
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
          <p className="tiny">
            <NavLink to="forgot">Forgot password</NavLink> · <NavLink to="signup">Create account</NavLink>
          </p>
        </form>
      </div>
    </div>
  )
}

export function SignupPage() {
  const { navigate } = useNavigation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [alert, setAlert] = useState('')
  const [mismatch, setMismatch] = useState(false)

  const submit = (event) => {
    event.preventDefault()
    setAlert('')
    setMismatch(false)
    if (!validEmail(email)) {
      setAlert('Enter a valid email.')
      return
    }
    if (password.length < 8) {
      setAlert('Password needs 8 or more characters.')
      return
    }
    if (password !== confirm) {
      setMismatch(true)
      return
    }
    navigate('verify')
  }

  return (
    <div className="auth">
      <AuthAside
        title="Get a gap report."
        copy="Create an account. Upload a spec. Review the evidence."
        note="Verify your email before analysis runs."
      />
      <div className="panel">
        <form className="acard" onSubmit={submit} noValidate>
          <h1>Create account</h1>
          <p className="sub">One option. Password needs 8 or more characters.</p>
          <div className={`alert alert-err${alert ? ' show' : ''}`} role="alert">{alert}</div>
          <div className="fieldf">
            <label htmlFor="sEmail">Email</label>
            <input
              className="input"
              id="sEmail"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <PasswordInput
            id="sPass"
            label="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <div className="fieldf">
            <label htmlFor="sPass2">Confirm password</label>
            <input
              className="input"
              id="sPass2"
              type="password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              required
            />
            <div className={`err${mismatch ? ' show' : ''}`} role="alert">Passwords do not match.</div>
          </div>
          <button className="btn btn-primary btn-full btn-lg" type="submit">Create account</button>
          <p className="tiny">
            By continuing you agree to the <NavLink to="terms">Terms</NavLink> and{' '}
            <NavLink to="privacy">Privacy policy</NavLink>.
          </p>
        </form>
      </div>
    </div>
  )
}

export function ForgotPage() {
  const emailRef = useRef(null)
  const [ok, setOk] = useState(false)

  const submit = (event) => {
    event.preventDefault()
    if (!validEmail(emailRef.current?.value.trim() || '')) {
      emailRef.current?.focus()
      return
    }
    setOk(true)
  }

  return (
    <div className="panel" style={{ minHeight: '52vh' }}>
      <form className="acard" onSubmit={submit} noValidate>
        <h1>Forgot password</h1>
        <p className="sub">If an account exists, we send a reset link. This preview sends no mail.</p>
        <div className={`alert alert-ok${ok ? ' show' : ''}`} role="status" aria-live="polite">
          If an account exists, a link is on its way.
        </div>
        <div className="fieldf">
          <label htmlFor="fEmail">Email</label>
          <input className="input" id="fEmail" ref={emailRef} type="email" required />
        </div>
        <button className="btn btn-primary btn-full btn-lg" type="submit">Send reset link</button>
        <p className="tiny"><NavLink to="login">Back to sign in</NavLink></p>
      </form>
    </div>
  )
}

export function ResetPage() {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [mismatch, setMismatch] = useState(false)
  const [ok, setOk] = useState(false)

  const submit = (event) => {
    event.preventDefault()
    setMismatch(false)
    setOk(false)
    if (password.length < 8) return
    if (password !== confirm) {
      setMismatch(true)
      return
    }
    setOk(true)
  }

  return (
    <div className="panel" style={{ minHeight: '52vh' }}>
      <form className="acard" onSubmit={submit} noValidate>
        <h1>Reset password</h1>
        <p className="sub">Pick a new one. 8 or more characters.</p>
        <div className={`alert alert-ok${ok ? ' show' : ''}`} role="status" aria-live="polite">
          Done in a live service. Sign in with the new password.
        </div>
        <PasswordInput
          id="rPass"
          label="New password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <div className="fieldf">
          <label htmlFor="rPass2">Confirm</label>
          <input
            className="input"
            id="rPass2"
            type="password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            required
          />
          <div className={`err${mismatch ? ' show' : ''}`} role="alert">Passwords do not match.</div>
        </div>
        <button className="btn btn-primary btn-full btn-lg" type="submit">Update password</button>
      </form>
    </div>
  )
}

export function VerifyPage() {
  return (
    <div className="panel" style={{ minHeight: '52vh' }}>
      <div className="acard">
        <h1>Verify your email</h1>
        <p className="sub">Open the link we sent to activate your account. Analysis stays off until you do.</p>
        <NavLink to="login" className="btn btn-primary">Return to sign in</NavLink>
      </div>
    </div>
  )
}
