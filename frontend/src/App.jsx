import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Footer, Header } from './components.jsx'
import { NavigationContext, PAGE_TITLES, normalizeRoute } from './navigation.js'
import {
  AboutPage,
  ContactPage,
  HomePage,
  HowPage,
  PricingPage,
  PrivacyPage,
  SamplePage,
  SecurityPage,
  TermsPage,
} from './pages/Marketing.jsx'
import {
  ForgotPage,
  LoginPage,
  ResetPage,
  SignupPage,
  VerifyPage,
} from './pages/Auth.jsx'

const PAGES = {
  home: HomePage,
  how: HowPage,
  sample: SamplePage,
  security: SecurityPage,
  pricing: PricingPage,
  about: AboutPage,
  contact: ContactPage,
  privacy: PrivacyPage,
  terms: TermsPage,
  login: LoginPage,
  signup: SignupPage,
  forgot: ForgotPage,
  reset: ResetPage,
  verify: VerifyPage,
}

function Page({ name, section, children }) {
  const rootRef = useRef(null)

  useEffect(() => {
    document.title = PAGE_TITLES[name] || PAGE_TITLES.home

    if (section === 'product') {
      const timer = window.setTimeout(() => {
        document.getElementById('product')?.scrollIntoView({ behavior: 'smooth' })
      }, 30)
      return () => window.clearTimeout(timer)
    }

    window.scrollTo(0, 0)
    const heading = rootRef.current?.querySelector('h1')
    if (heading) {
      heading.setAttribute('tabindex', '-1')
      heading.focus({ preventScroll: true })
    }
    return undefined
  }, [name, section])

  useEffect(() => {
    const root = rootRef.current
    if (!root) return undefined

    const items = Array.from(root.querySelectorAll('.reveal:not(.in)'))
    if (!('IntersectionObserver' in window)) {
      items.forEach((item) => item.classList.add('in'))
      return undefined
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return
          entry.target.classList.add('in')
          observer.unobserve(entry.target)
        })
      },
      { threshold: 0.12 },
    )
    items.forEach((item) => observer.observe(item))
    return () => observer.disconnect()
  }, [name])

  return (
    <div className="page on" data-page={name} ref={rootRef}>
      {children}
    </div>
  )
}

export default function App() {
  const [route, setRoute] = useState(() => normalizeRoute(window.location.hash))
  const [section, setSection] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onLocationChange = () => {
      setRoute(normalizeRoute(window.location.hash))
      setSection(null)
    }
    window.addEventListener('hashchange', onLocationChange)
    window.addEventListener('popstate', onLocationChange)
    return () => {
      window.removeEventListener('hashchange', onLocationChange)
      window.removeEventListener('popstate', onLocationChange)
    }
  }, [])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const navigate = useCallback((name, extra = null) => {
    const next = normalizeRoute(`#${name}`)
    setRoute(next)
    setSection(extra || null)
    setMenuOpen(false)
    try {
      window.history.pushState(null, '', `#${next}`)
    } catch {
      setRoute(next)
    }
  }, [])

  const navigationValue = useMemo(() => ({ route, navigate }), [route, navigate])
  const ActivePage = PAGES[route] || HomePage

  return (
    <NavigationContext.Provider value={navigationValue}>
      <a className="skip" href="#main">Skip to content</a>
      <Header
        menuOpen={menuOpen}
        onToggleMenu={() => setMenuOpen((open) => !open)}
        scrolled={scrolled}
      />
      <main id="main">
        <Page key={route} name={route} section={section}>
          <ActivePage />
        </Page>
      </main>
      <Footer />
    </NavigationContext.Provider>
  )
}
