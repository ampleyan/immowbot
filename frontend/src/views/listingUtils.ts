type Listing = {
  url?: string
  source?: string
  source_listing_id?: string | number
  _score?: number | null
  price?: number
  surface_area?: number
  bedrooms?: number
  _first_seen_at?: string
  _workflow?: { next_follow_up_date?: string | null }
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

export function listingKey(listing: Listing): string {
  return `${listing.source || ''}:${listing.source_listing_id || listing.url || ''}`
}

export function formatListingAddress(listing: Record<string, unknown>): string {
  const street = [listing.street, listing.house_number].filter(Boolean).join(' ')
  const locality = [listing.city, listing.postcode].filter(Boolean).join(', ')
  return [street || listing.address, locality].filter(Boolean).join(', ') || 'Address unavailable'
}

export function matchesTriage(listing: Listing, filter: string, changedKeys: Set<string>, now = Date.now()): boolean {
  if (filter === 'new') return isNewListing(listing, now)
  if (filter === 'changed') return changedKeys.has(listingKey(listing))
  if (filter === 'follow-up') return Boolean(listing._workflow?.next_follow_up_date)
  return true
}
