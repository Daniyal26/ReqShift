import { createContext, useContext } from 'react'

export const PAGE_NAMES = [
  'home', 'how', 'analyze', 'security', 'pricing', 'about',
  'privacy', 'terms',
]

export const PAGE_TITLES = {
  home: 'ReqShift | Find the gaps before you build',
  how: 'How it works | ReqShift',
  analyze: 'Live analysis | ReqShift',
  security: 'Security | ReqShift',
  pricing: 'Pilot | ReqShift',
  about: 'About | ReqShift',
  privacy: 'Privacy policy | ReqShift',
  terms: 'Terms of use | ReqShift',
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
