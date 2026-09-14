type Listing = {
  url?: string
  source?: string
  source_listing_id?: string | number
  _score?: number | null
  price?: number
  surface_area?: number
  bedrooms?: number
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
}

export function sortListings(listings: Listing[], sortBy: string): Listing[] {
  const accessor = SORT_ACCESSORS[sortBy] ?? SORT_ACCESSORS.score!
  const direction = sortBy === 'score' || sortBy === 'priceHigh' || sortBy === 'surface' || sortBy === 'bedrooms' || sortBy === 'dateAdded' ? -1 : 1
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
