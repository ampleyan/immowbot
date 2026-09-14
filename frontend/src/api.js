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
  checkInvite: (token) => req('GET', `/register/${token}`),
  register: (token, username, password) => req('POST', `/register/${token}`, { username, password }),
  checkTrusted: () => req('GET', '/auth/trusted'),
  loginTrusted: () => req('POST', '/auth/login-trusted'),
  me: () => req('GET', '/auth/me'),
  logout: () => req('POST', '/auth/logout'),
  listings: () => req('GET', '/listings'),
  getConfig: () => req('GET', '/config'),
  updateConfig: (data) => req('PUT', '/config', data),
  getRuns: () => req('GET', '/runs'),
  getRunListings: (id) => req('GET', `/runs/${id}/listings`),
  startRun: () => req('POST', '/runs'),
  startSelectedRun: (listings) => req('POST', '/runs/selected', { listings }),
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
  getSmartLists: () => req('GET', '/smart-lists'),
  createSmartList: (name, rule) => req('POST', '/smart-lists', { name, rule }),
  updateSmartList: (id, data) => req('PATCH', `/smart-lists/${id}`, data),
  deleteSmartList: (id) => req('DELETE', `/smart-lists/${id}`),
  getSmartListItems: (id) => req('GET', `/smart-lists/${id}/items`),
  getListingChanges: (source, sid) => req('GET', `/changes/${source}/${sid}`),
  getWorkflow: (source, sid) => req('GET', `/workflow/${source}/${sid}`),
  saveWorkflow: (source, sid, data) => req('PUT', `/workflow/${source}/${sid}`, data),
  getInteractions: (source, sid) => req('GET', `/interactions/${source}/${sid}`),
  addInteraction: (source, sid, data) => req('POST', `/interactions/${source}/${sid}`, data),
  getDuplicates: () => req('GET', '/duplicates'),
  mergeDuplicates: (keep, remove) => req('POST', '/duplicates/merge', { keep, remove }),
  getAlerts: () => req('GET', '/alerts'),
  markAlertRead: (id) => req('POST', `/alerts/${id}/read`),
  clearAlerts: () => req('DELETE', '/alerts'),
}
