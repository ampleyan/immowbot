import { describe, expect, it } from 'vitest'
import { formatListingAddress, getFollowUps, hasInsufficientPictures, isNewListing, isPendingReview, matchesTriage, potentialBenefits, sortListings } from '../listingUtils.js'

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

  it('sorts by most recently updated, then newest created when update times tie', () => {
    const dated = [
      { url: 'older-update', _last_updated_at: '2026-09-13T09:00:00Z', _first_seen_at: '2026-09-13T08:00:00Z' },
      { url: 'newer-update', _last_updated_at: '2026-09-13T11:00:00Z', _first_seen_at: '2026-09-10T08:00:00Z' },
      { url: 'newer-created-tie', _last_updated_at: '2026-09-13T09:00:00Z', _first_seen_at: '2026-09-13T10:00:00Z' },
      { url: 'missing-update', _first_seen_at: '2026-09-11T08:00:00Z' },
    ]

    expect(sortListings(dated, 'lastUpdated').map(listing => listing.url)).toEqual([
      'newer-update', 'newer-created-tie', 'older-update', 'missing-update',
    ])
  })

  it('recognizes listings first seen within the last day', () => {
    const now = Date.parse('2026-09-13T12:00:00Z')
    expect(isNewListing({ _first_seen_at: '2026-09-13T11:00:00Z' }, now)).toBe(true)
    expect(isNewListing({ _first_seen_at: '2026-09-11T12:00:00Z' }, now)).toBe(false)
  })
})

describe('formatListingAddress', () => {
  it('combines street, house number, city, and postcode', () => {
    expect(formatListingAddress({ street: 'Main Street', house_number: '12', city: 'Antwerp', postcode: '2000' })).toBe('Main Street 12, Antwerp, 2000')
  })

  it('uses location when structured address fields are missing', () => {
    expect(formatListingAddress({ location: 'Antwerpen, 2020, Pieter Genardstraat 6' })).toBe('Antwerpen, 2020, Pieter Genardstraat 6')
  })

  it('uses an address-like listing name as a fallback', () => {
    expect(formatListingAddress({ name: 'Van Maerlantstraat 56, 2000 Antwerpen' })).toBe('Van Maerlantstraat 56, 2000 Antwerpen')
  })
})

describe('hasInsufficientPictures', () => {
  it('treats listings with fewer than three usable pictures as incomplete', () => {
    expect(hasInsufficientPictures({ images: ['https://example.test/one.jpg', 'https://example.test/two.jpg'] })).toBe(true)
    expect(hasInsufficientPictures({ images: ['https://example.test/one.jpg', 'https://example.test/two.jpg', 'https://example.test/three.jpg'] })).toBe(false)
  })

  it('counts numbered detail pictures with the gallery pictures', () => {
    expect(hasInsufficientPictures({ all_property_details: { 'Image 1 URL': 'https://example.test/one.jpg', 'Image 2 URL': 'https://example.test/two.jpg', 'Image 3 URL': 'https://example.test/three.jpg' } })).toBe(false)
  })
})

describe('potentialBenefits', () => {
  it('marks new builds, efficient homes, and older low-EPC homes', () => {
    expect(potentialBenefits({ construction_year: 2025, epc_score: 'A' })).toEqual([
      'New build / VAT check',
      'Energy / green finance check',
    ])
    expect(potentialBenefits({ construction_year: 1980, epc_score: 'F' })).toEqual(['Renovation support check'])
  })
})

describe('isPendingReview', () => {
  it('keeps new listings active and removes pipeline-reviewed listings', () => {
    expect(isPendingReview({ _workflow: { status: 'New' } })).toBe(true)
    expect(isPendingReview({})).toBe(true)
    expect(isPendingReview({ _workflow: { status: 'Interested' } })).toBe(false)
  })

  it('treats a saved note as reviewed', () => {
    expect(isPendingReview({ _workflow: { status: 'New' }, _note: 'Call back next week' })).toBe(false)
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

describe('matchesTriage', () => {
  it('filters new, changed, and follow-up listings', () => {
    const now = Date.parse('2026-09-14T12:00:00Z')
    const listing = { source: 'immoweb', source_listing_id: '1', _first_seen_at: '2026-09-14T11:00:00Z', _workflow: { next_follow_up_date: '2026-09-15' } }

    expect(matchesTriage(listing, 'new', new Set(), now)).toBe(true)
    expect(matchesTriage(listing, 'changed', new Set(['immoweb:1']), now)).toBe(true)
    expect(matchesTriage(listing, 'follow-up', new Set(), now)).toBe(true)
    expect(matchesTriage(listing, 'changed', new Set(), now)).toBe(false)
  })
})
