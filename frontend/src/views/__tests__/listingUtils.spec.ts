import { describe, expect, it } from 'vitest'
import { sortListings } from '../listingUtils.js'

const listings = [
  { url: 'low', price: 200000, surface_area: 80, bedrooms: 2, _score: 55 },
  { url: 'high', price: 400000, surface_area: 120, bedrooms: 4, _score: 82 },
  { url: 'mid', price: 300000, surface_area: 100, bedrooms: 3, _score: 68 },
]

describe('sortListings', () => {
  it('sorts best matches first by default', () => {
    expect(sortListings(listings, 'score').map(listing => listing.url)).toEqual(['high', 'mid', 'low'])
  })

  it('sorts prices from low to high', () => {
    expect(sortListings(listings, 'price').map(listing => listing.url)).toEqual(['low', 'mid', 'high'])
  })

  it('sorts prices from high to low', () => {
    expect(sortListings(listings, 'priceHigh').map(listing => listing.url)).toEqual(['high', 'mid', 'low'])
  })
})
