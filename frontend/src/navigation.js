import { createContext, useContext } from 'react'

export const PAGE_NAMES = [
  'home', 'how', 'sample', 'security', 'pricing', 'about', 'contact',
  'privacy', 'terms', 'login', 'signup', 'forgot', 'reset', 'verify',
]

export const PAGE_TITLES = {
  home: 'ReqShift | Find the gaps before you build',
  how: 'How it works | ReqShift',
  sample: 'Sample report | ReqShift',
  security: 'Security | ReqShift',
  pricing: 'Pilot | ReqShift',
  about: 'About | ReqShift',
  contact: 'Contact | ReqShift',
  privacy: 'Privacy policy | ReqShift',
  terms: 'Terms of use | ReqShift',
  login: 'Sign in | ReqShift',
  signup: 'Create account | ReqShift',
  forgot: 'Forgot password | ReqShift',
  reset: 'Reset password | ReqShift',
  verify: 'Verify email | ReqShift',
}

export const NavigationContext = createContext({
  route: 'home',
  navigate: () => {},
})

export function useNavigation() {
  return useContext(NavigationContext)
}

export function normalizeRoute(hash) {
  const raw = (hash || '#home').slice(1)
  const name = raw.split('/')[0] || 'home'
  return PAGE_NAMES.includes(name) ? name : 'home'
}
