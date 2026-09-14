import { describe, expect, it } from 'vitest'
import { getFollowUps, isNewListing, sortListings } from '../listingUtils.js'

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

  it('sorts by date added with newest first', () => {
    const dated = [
      { url: 'old', _first_seen_at: '2026-09-10T12:00:00Z' },
      { url: 'new', _first_seen_at: '2026-09-13T12:00:00Z' },
      { url: 'missing' },
    ]
    expect(sortListings(dated, 'dateAdded').map(listing => listing.url)).toEqual(['new', 'old', 'missing'])
  })

  it('recognizes listings first seen within the last day', () => {
    const now = Date.parse('2026-09-13T12:00:00Z')
    expect(isNewListing({ _first_seen_at: '2026-09-13T11:00:00Z' }, now)).toBe(true)
    expect(isNewListing({ _first_seen_at: '2026-09-11T12:00:00Z' }, now)).toBe(false)
  })
})

describe('getFollowUps', () => {
  it('orders overdue and due follow-ups before future ones', () => {
    const items = [
      { url: 'future', _workflow: { next_follow_up_date: '2026-09-20' } },
      { url: 'today', _workflow: { next_follow_up_date: '2026-09-14' } },
      { url: 'overdue', _workflow: { next_follow_up_date: '2026-09-12' } },
      { url: 'none', _workflow: {} },
    ]

    expect(getFollowUps(items).map(listing => listing.url)).toEqual(['overdue', 'today', 'future'])
  })
})
