type Listing = {
  url?: string
  _score?: number | null
  price?: number
  surface_area?: number
  bedrooms?: number
  _first_seen_at?: string
}

const SORT_ACCESSORS: Record<string, (listing: Listing) => number> = {
  score: listing => listing._score ?? -Infinity,
  price: listing => listing.price ?? Infinity,
  priceHigh: listing => listing.price ?? -Infinity,
  surface: listing => listing.surface_area ?? -Infinity,
  bedrooms: listing => listing.bedrooms ?? -Infinity,
}

export function sortListings(listings: Listing[], sortBy: string): Listing[] {
  const accessor = SORT_ACCESSORS[sortBy] ?? SORT_ACCESSORS.score!
  const direction = sortBy === 'score' || sortBy === 'priceHigh' || sortBy === 'surface' || sortBy === 'bedrooms' ? -1 : 1
  return [...listings].sort((a, b) => (accessor(a) - accessor(b)) * direction)
}

export function isNewListing(listing: Listing, now = Date.now()): boolean {
  if (!listing._first_seen_at) return false
  const firstSeen = Date.parse(listing._first_seen_at)
  return Number.isFinite(firstSeen) && now - firstSeen >= 0 && now - firstSeen <= 24 * 60 * 60 * 1000
}
