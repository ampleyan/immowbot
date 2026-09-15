type Listing = {
  url?: string
  source?: string
  source_listing_id?: string | number
  _score?: number | null
  price?: number
  surface_area?: number
  bedrooms?: number
  latitude?: number | string | null
  longitude?: number | string | null
  _first_seen_at?: string
  construction_year?: number
  epc_score?: string
  _purchase_estimate?: { is_new_build?: boolean }
  image_url_1?: string | null
  image_url_2?: string | null
  images?: unknown[]
  all_property_details?: Record<string, unknown>
  _workflow?: { status?: string; next_follow_up_date?: string | null }
}

const GROTE_MARKT = { lat: 51.2213, lon: 4.3997 }

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

const SORT_ACCESSORS: Record<string, (listing: Listing) => number> = {
  score: listing => listing._score ?? -Infinity,
  price: listing => listing.price ?? Infinity,
  priceHigh: listing => listing.price ?? -Infinity,
  surface: listing => listing.surface_area ?? -Infinity,
  bedrooms: listing => listing.bedrooms ?? -Infinity,
  dateAdded: listing => {
    const timestamp = listing._first_seen_at ? Date.parse(listing._first_seen_at) : NaN
    return Number.isFinite(timestamp) ? timestamp : -Infinity
  },
  distance: listing => {
    const lat = Number(listing.latitude)
    const lon = Number(listing.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return Infinity
    return haversineKm(lat, lon, GROTE_MARKT.lat, GROTE_MARKT.lon)
  },
}

export function sortListings(listings: Listing[], sortBy: string): Listing[] {
  const accessor = SORT_ACCESSORS[sortBy] ?? SORT_ACCESSORS.score!
  const descending = new Set(['score', 'priceHigh', 'surface', 'bedrooms', 'dateAdded'])
  const direction = descending.has(sortBy) ? -1 : 1
  return [...listings].sort((a, b) => (accessor(a) - accessor(b)) * direction)
}

export function isNewListing(listing: Listing, now = Date.now()): boolean {
  if (!listing._first_seen_at) return false
  const firstSeen = Date.parse(listing._first_seen_at)
  return Number.isFinite(firstSeen) && now - firstSeen >= 0 && now - firstSeen <= 24 * 60 * 60 * 1000
}

export function getFollowUps(listings: Listing[]): Listing[] {
  return listings
    .filter(listing => listing._workflow?.next_follow_up_date)
    .sort((a, b) => (a._workflow!.next_follow_up_date! > b._workflow!.next_follow_up_date! ? 1 : -1))
}

export function isPendingReview(listing: Listing): boolean {
  return !listing._workflow?.status || listing._workflow.status === 'New'
}

export function listingKey(listing: Listing): string {
  return `${listing.source || ''}:${listing.source_listing_id || listing.url || ''}`
}

export function hasInsufficientPictures(listing: Listing): boolean {
  const details = listing.all_property_details || {}
  const detailImages = Object.entries(details)
    .filter(([key]) => /^Image \d+ URL$/i.test(key))
    .map(([, value]) => value)
  const candidates = [listing.image_url_1, listing.image_url_2, ...(listing.images || []), ...detailImages]
  const usable = new Set(candidates.filter(value => typeof value === 'string' && value.startsWith('http')))
  return usable.size < 3
}

export function potentialBenefits(listing: Listing): string[] {
  const benefits: string[] = []
  const year = Number(listing.construction_year)
  const epc = String(listing.epc_score || '').trim().toUpperCase()
  if (listing._purchase_estimate?.is_new_build || year >= 2024) benefits.push('New build / VAT check')
  if (['A++', 'A+', 'A', 'B'].includes(epc)) benefits.push('Energy / green finance check')
  if (year > 0 && year <= 2000 && ['E', 'F', 'G'].includes(epc)) benefits.push('Renovation support check')
  return benefits
}

export function formatListingAddress(listing: Record<string, unknown>): string {
  const text = (value: unknown) => typeof value === 'string' || typeof value === 'number' ? String(value).trim() : ''
  const street = [text(listing.street), text(listing.house_number)].filter(Boolean).join(' ')
  const locality = [text(listing.city), text(listing.postcode)].filter(Boolean).join(', ')
  const address = text(listing.address)
  const location = text(listing.location)
  const name = text(listing.name)
  const namedAddress = /\d/.test(name) ? name : ''
  const structuredAddress = street || address
  return structuredAddress
    ? [structuredAddress, locality].filter(Boolean).join(', ')
    : location || namedAddress || locality || 'Address unavailable'
}

export function matchesTriage(listing: Listing, filter: string, changedKeys: Set<string>, now = Date.now()): boolean {
  if (filter === 'new') return isNewListing(listing, now)
  if (filter === 'changed') return changedKeys.has(listingKey(listing))
  if (filter === 'follow-up') return Boolean(listing._workflow?.next_follow_up_date)
  return true
}
