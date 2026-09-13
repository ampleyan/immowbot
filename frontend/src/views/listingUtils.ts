type Listing = {
  url?: string
  _score?: number | null
  price?: number
  surface_area?: number
  bedrooms?: number
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
