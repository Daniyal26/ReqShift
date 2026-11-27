export async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: options.body
      ? { 'Content-Type': 'application/json', ...(options.headers || {}) }
      : options.headers,
  })

  let data
  try {
    data = await response.json()
  } catch {
    throw new Error(`Server returned ${response.status}`)
  }

  if (!response.ok || data.error) {
    throw new Error(data.error || `Request failed (${response.status})`)
  }
  return data
}

export const getBackends = () => apiFetch('/api/backends')
export const getExamples = () => apiFetch('/api/examples')
export const getExample = (name) => apiFetch(`/api/example?name=${encodeURIComponent(name)}`)

export const readPdf = (name, data) => apiFetch('/api/read', {
  method: 'POST',
  body: JSON.stringify({ name, data }),
})

export const startAnalysis = (body) => apiFetch('/api/analyze', {
  method: 'POST',
  body: JSON.stringify(body),
})

export const getJob = (id) => apiFetch(`/api/job?id=${encodeURIComponent(id)}`)

export const saveReport = (payload) => apiFetch('/api/save', {
  method: 'POST',
  body: JSON.stringify(payload),
})

// Step 2. Re-proves an existing model with numbers the reader supplied. No AI call.
export const reanalyze = (body) => apiFetch('/api/reanalyze', {
  method: 'POST',
  body: JSON.stringify(body),
})
