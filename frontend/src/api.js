const BASE = '/api'

async function req(method, path, body) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const r = await fetch(BASE + path, opts)
  const text = await r.text()
  if (!r.ok) throw new Error(text || `Request failed (${r.status})`)
  if (!text.trim()) throw new Error(`Empty response from ${method} ${path}`)
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`Invalid JSON from ${method} ${path}`)
  }
}

export const api = {
  login: (username, password) => req('POST', '/auth/login', { username, password }),
  me: () => req('GET', '/auth/me'),
  logout: () => req('POST', '/auth/logout'),
  listings: () => req('GET', '/listings'),
  getConfig: () => req('GET', '/config'),
  updateConfig: (data) => req('PUT', '/config', data),
  getRuns: () => req('GET', '/runs'),
  getRunListings: (id) => req('GET', `/runs/${id}/listings`),
  startRun: () => req('POST', '/runs'),
  cancelRun: () => req('DELETE', '/runs/active'),
  getLists: () => req('GET', '/lists'),
  createList: (name) => req('POST', '/lists', { name }),
  deleteList: (id) => req('DELETE', `/lists/${id}`),
  getListItems: (id) => req('GET', `/lists/${id}/items`),
  addToList: (listId, source, sid) => req('POST', `/lists/${listId}/items`, { source, source_listing_id: sid }),
  removeFromList: (listId, source, sid) => req('DELETE', `/lists/${listId}/items/${source}/${sid}`),
  getNote: (source, sid) => req('GET', `/notes/${source}/${sid}`),
  saveNote: (source, sid, note) => req('PUT', `/notes/${source}/${sid}`, { note }),
  deleteListing: (source, sid) => req('DELETE', `/listings/${source}/${sid}`),
}
