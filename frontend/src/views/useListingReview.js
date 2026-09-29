import { computed, ref, watch } from 'vue'
import {
  getFollowUps,
  hasInsufficientPictures,
  isPendingReview,
  matchesTriage,
  potentialBenefits,
  sortListings,
} from './listingUtils.js'

const FILTER_DEFAULTS = {
  sources: [], postcodes: [], epc: [], benefits: [],
  minBeds: 0, minSqm: 0, maxSqm: 0,
  minPrice: 0, maxPrice: 0, minScore: 0, maxScore: 0,
  minYear: 0, maxYear: 0, maxMonthlyCharges: 0,
  minRating: 0,
  terrace: false, hasParking: false, ownerOccupied: false, includeUnderOption: true,
  withoutPicture: false, withDescription: false, dutchOnly: false,
}

const VALID_TRIAGE_FILTERS = ['all', 'new', 'changed', 'follow-up']
const ALL_EPC = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
const WORKFLOW_STATUSES = ['Interested', 'Contacted', 'Visit planned', 'Offer', 'On hold', 'Rejected']

function loadSavedFilters() {
  try {
    const saved = localStorage.getItem('listing-filters')
    if (saved) return { ...FILTER_DEFAULTS, ...JSON.parse(saved) }
  } catch {}
  return { ...FILTER_DEFAULTS }
}

export function useListingReview({ listings, alerts, initialTriageFilter }) {
  const filters = ref(loadSavedFilters())
  const selectedUrl = ref(null)
  const checked = ref(new Set())
  const showExcluded = ref(false)
  const filterOpen = ref(false)
  const advancedFiltersOpen = ref(false)
  const sortBy = ref('lastUpdated')
  const comparisonOpen = ref(false)
  const mapOpen = ref(localStorage.getItem('map-open') === 'true')
  const mapBoundsFilter = ref(false)
  const mapOnlyFocused = ref(false)
  const mapBounds = ref(null)
  const triageFilter = ref(VALID_TRIAGE_FILTERS.includes(initialTriageFilter()) ? initialTriageFilter() : 'all')
  const statusFilter = ref('pending')
  const mapModalUrl = ref(null)
  const searchQuery = ref('')

  watch(initialTriageFilter, value => {
    triageFilter.value = VALID_TRIAGE_FILTERS.includes(value) ? value : 'all'
  })
  watch(filters, value => localStorage.setItem('listing-filters', JSON.stringify(value)), { deep: true })
  watch(mapOpen, value => localStorage.setItem('map-open', String(value)))

  const selectedListing = computed(() => selectedUrl.value
    ? listings.value.find(listing => listing.url === selectedUrl.value) || null
    : null)
  const mapListings = computed(() => selectedListing.value && !displayList.value.some(listing => listing.url === selectedListing.value.url)
    ? [...displayList.value, selectedListing.value]
    : displayList.value)
  const selectedHasCoordinates = computed(() => {
    const listing = selectedListing.value
    return !!listing && Number.isFinite(Number(listing.latitude)) && listing.latitude !== null && listing.latitude !== '' && Number.isFinite(Number(listing.longitude)) && listing.longitude !== null && listing.longitude !== ''
  })
  const mapModalListing = computed(() => mapModalUrl.value
    ? listings.value.find(listing => listing.url === mapModalUrl.value) || null
    : null)

  const passing = computed(() => listings.value.filter(listing => !listing._exclusions?.length))
  const excluded = computed(() => listings.value.filter(listing => listing._exclusions?.length > 0))
  const reviewQueue = computed(() => listings.value.filter(isPendingReview))
  const reviewedListings = computed(() => sortListings(listings.value.filter(listing => !isPendingReview(listing)), sortBy.value))
  const followUps = computed(() => getFollowUps(listings.value))
  const changedKeys = computed(() => new Set(alerts.value
    .filter(alert => alert.kind === 'price_reduction' || alert.kind === 'photos_added')
    .map(alert => `${alert.source}:${alert.source_listing_id}`)))
  const triageCounts = computed(() => ({
    all: reviewQueue.value.filter(listing => !listing._exclusions?.length).length,
    new: reviewQueue.value.filter(listing => !listing._exclusions?.length && matchesTriage(listing, 'new', changedKeys.value)).length,
    changed: reviewQueue.value.filter(listing => !listing._exclusions?.length && matchesTriage(listing, 'changed', changedKeys.value)).length,
    'follow-up': reviewQueue.value.filter(listing => !listing._exclusions?.length && matchesTriage(listing, 'follow-up', changedKeys.value)).length,
  }))

  const statusCounts = computed(() => {
    const counts = { pending: 0, Interested: 0, Contacted: 0, 'Visit planned': 0, Offer: 0, 'On hold': 0, Rejected: 0 }
    for (const listing of listings.value) {
      const status = listing._workflow?.status
      if (!status || status === 'New') counts.pending++
      else if (status in counts) counts[status]++
    }
    return counts
  })
  const activeStatusSource = computed(() => statusFilter.value === 'pending'
    ? reviewQueue.value
    : listings.value.filter(listing => listing._workflow?.status === statusFilter.value))
  const filterableListings = computed(() => {
    const base = activeStatusSource.value
    return showExcluded.value ? base : base.filter(listing => !listing._exclusions?.length)
  })
  const availableSources = computed(() => [...new Set(filterableListings.value.map(listing => listing.source).filter(Boolean))].sort())
  const availablePostcodes = computed(() => [...new Set(filterableListings.value.map(listing => listing.postcode).filter(Boolean))].sort())
  const availableEpc = computed(() => ALL_EPC.filter(epc => filterableListings.value.some(listing => listing.epc_score === epc)))
  const availableBenefits = computed(() => [...new Set(filterableListings.value.flatMap(potentialBenefits))].sort())

  const displayList = computed(() => {
    const base = activeStatusSource.value
    const basePassing = base.filter(listing => !listing._exclusions?.length)
    const baseExcluded = base.filter(listing => listing._exclusions?.length > 0)
    let list = [...basePassing, ...(showExcluded.value ? baseExcluded : [])]
    const filter = filters.value
    if (filter.sources.length) list = list.filter(listing => filter.sources.includes(listing.source))
    if (filter.postcodes.length) list = list.filter(listing => filter.postcodes.includes(listing.postcode))
    if (filter.epc.length) list = list.filter(listing => filter.epc.includes(listing.epc_score))
    if (filter.minBeds > 0) list = list.filter(listing => (listing.bedrooms || 0) >= filter.minBeds)
    if (filter.minSqm > 0) list = list.filter(listing => (listing.surface_area || 0) >= filter.minSqm)
    if (filter.maxSqm > 0) list = list.filter(listing => (listing.surface_area || 0) <= filter.maxSqm)
    if (filter.minPrice > 0) list = list.filter(listing => (listing.price || 0) >= filter.minPrice)
    if (filter.maxPrice > 0) list = list.filter(listing => (listing.price || 0) <= filter.maxPrice)
    if (filter.minScore > 0) list = list.filter(listing => listing._score != null && listing._score >= filter.minScore)
    if (filter.minRating > 0) list = list.filter(listing => (listing._workflow?.rating || 0) >= filter.minRating)
    if (filter.maxScore > 0) list = list.filter(listing => listing._score != null && listing._score <= filter.maxScore)
    if (filter.minYear > 0) list = list.filter(listing => listing.construction_year && listing.construction_year >= filter.minYear)
    if (filter.maxYear > 0) list = list.filter(listing => listing.construction_year && listing.construction_year <= filter.maxYear)
    if (filter.terrace) list = list.filter(listing => listing.outdoor_terrace || listing.outdoor_garden || listing.outdoor_surface)
    if (filter.hasParking) list = list.filter(listing => {
      const details = listing.all_property_details || {}
      return details['Garage'] || details['Parking indoor'] || details['Parking outdoor'] || details['Parking closed box'] || listing.garage || listing.parking
    })
    if (filter.ownerOccupied) list = list.filter(listing => !listing.has_tenant)
    if (!filter.includeUnderOption) list = list.filter(listing => !listing.under_option)
    if (filter.maxMonthlyCharges > 0) list = list.filter(listing => !listing.monthly_charges || Number(listing.monthly_charges) <= filter.maxMonthlyCharges)
    if (filter.withoutPicture) list = list.filter(hasInsufficientPictures)
    if (filter.withDescription) list = list.filter(listing => listing.description)
    if (filter.dutchOnly) list = list.filter(listing => listing.description && (!listing.description_english || listing.description_english === listing.description))
    if (filter.benefits.length) list = list.filter(listing => filter.benefits.every(benefit => potentialBenefits(listing).includes(benefit)))
    if (mapBoundsFilter.value && mapBounds.value) {
      const { north, south, east, west } = mapBounds.value
      list = list.filter(listing => {
        const latitude = Number(listing.latitude), longitude = Number(listing.longitude)
        return Number.isFinite(latitude) && Number.isFinite(longitude) && latitude >= south && latitude <= north && longitude >= west && longitude <= east
      })
    }
    if (statusFilter.value === 'pending') list = list.filter(listing => (showExcluded.value && listing._exclusions?.length) || matchesTriage(listing, triageFilter.value, changedKeys.value))
    const query = searchQuery.value.trim().toLowerCase()
    if (query) list = list.filter(listing => {
      const haystack = [
        listing.source_listing_id, listing.postcode, listing.street, listing.city, listing.municipality, listing.address,
        listing.description_english, listing.description,
      ].filter(Boolean).join(' ').toLowerCase()
      return haystack.includes(query)
    })
    const matching = sortListings(list.filter(listing => !listing._exclusions?.length), sortBy.value)
    const excludedResults = sortListings(list.filter(listing => listing._exclusions?.length > 0), sortBy.value)
    return [...matching, ...(showExcluded.value ? excludedResults : [])]
  })

  const nChecked = computed(() => checked.value.size)
  const comparisonListings = computed(() => listings.value.filter(listing => !listing._is_duplicate && checked.value.has(listing.url)).slice(0, 5))
  const withoutCoordinates = computed(() => displayList.value.filter(listing => listing.latitude === null || listing.latitude === undefined || listing.latitude === '' || listing.longitude === null || listing.longitude === undefined || listing.longitude === '' || !Number.isFinite(Number(listing.latitude)) || !Number.isFinite(Number(listing.longitude))).length)
  const activeFilterCount = computed(() => {
    const filter = filters.value
    return filter.sources.length + filter.postcodes.length + filter.epc.length + filter.benefits.length +
      (filter.minBeds > 0 ? 1 : 0) + (filter.minSqm > 0 ? 1 : 0) + (filter.maxSqm > 0 ? 1 : 0) +
      (filter.minPrice > 0 ? 1 : 0) + (filter.maxPrice > 0 ? 1 : 0) +
      (filter.minScore > 0 ? 1 : 0) + (filter.maxScore > 0 ? 1 : 0) +
      (filter.minRating > 0 ? 1 : 0) + (filter.minYear > 0 ? 1 : 0) + (filter.maxYear > 0 ? 1 : 0) +
      (filter.terrace ? 1 : 0) + (filter.hasParking ? 1 : 0) + (filter.ownerOccupied ? 1 : 0) + (filter.includeUnderOption ? 0 : 1) +
      (filter.maxMonthlyCharges > 0 ? 1 : 0) + (filter.withoutPicture ? 1 : 0) + (filter.withDescription ? 1 : 0) + (filter.dutchOnly ? 1 : 0)
  })
  const advancedFilterCount = computed(() => {
    const filter = filters.value
    return (filter.minBeds > 0 ? 1 : 0) + (filter.minSqm > 0 ? 1 : 0) + (filter.maxSqm > 0 ? 1 : 0) +
      (filter.minPrice > 0 ? 1 : 0) + (filter.maxPrice > 0 ? 1 : 0) +
      (filter.minScore > 0 ? 1 : 0) + (filter.maxScore > 0 ? 1 : 0) + (filter.minRating > 0 ? 1 : 0) +
      (filter.minYear > 0 ? 1 : 0) + (filter.maxYear > 0 ? 1 : 0) + (filter.maxMonthlyCharges > 0 ? 1 : 0) +
      (filter.terrace ? 1 : 0) + (filter.hasParking ? 1 : 0) + (filter.ownerOccupied ? 1 : 0) +
      (!filter.includeUnderOption ? 1 : 0) + (filter.withoutPicture ? 1 : 0) + (filter.withDescription ? 1 : 0) + (filter.dutchOnly ? 1 : 0)
  })
  if (advancedFilterCount.value) advancedFiltersOpen.value = true
  watch(advancedFilterCount, count => {
    if (count) advancedFiltersOpen.value = true
  })

  const sqmRange = computed({
    get: () => [filters.value.minSqm, filters.value.maxSqm || 500],
    set: ([low, high]) => { filters.value.minSqm = low; filters.value.maxSqm = high === 500 ? 0 : high },
  })
  const priceRange = computed({
    get: () => [filters.value.minPrice, filters.value.maxPrice || 2000000],
    set: ([low, high]) => { filters.value.minPrice = low; filters.value.maxPrice = high === 2000000 ? 0 : high },
  })
  const scoreRange = computed({
    get: () => [filters.value.minScore, filters.value.maxScore || 100],
    set: ([low, high]) => { filters.value.minScore = low; filters.value.maxScore = high === 100 ? 0 : high },
  })
  const yearRange = computed({
    get: () => [filters.value.minYear || 1900, filters.value.maxYear || 2025],
    set: ([low, high]) => { filters.value.minYear = low === 1900 ? 0 : low; filters.value.maxYear = high === 2025 ? 0 : high },
  })

  function clearFilters() {
    filters.value = { ...FILTER_DEFAULTS }
  }

  function removeSingleChipFilter(key, value) {
    filters.value[key] = filters.value[key].filter(item => item !== value)
  }

  function toggleCheck(url) {
    const selection = new Set(checked.value)
    if (selection.has(url)) selection.delete(url)
    else selection.add(url)
    checked.value = selection
  }

  function selectAll() {
    checked.value = new Set(displayList.value.filter(listing => !listing._is_duplicate).map(listing => listing.url))
  }

  function deselectAll() {
    checked.value = new Set()
  }

  function removeComparison(url) {
    const selection = new Set(checked.value)
    selection.delete(url)
    checked.value = selection
  }

  function openMapDetail(url) {
    mapModalUrl.value = url
  }

  return {
    filters, selectedUrl, checked, showExcluded, filterOpen, advancedFiltersOpen, sortBy, comparisonOpen,
    mapOpen, mapBoundsFilter, mapOnlyFocused, mapBounds, triageFilter, statusFilter, mapModalUrl, searchQuery,
    selectedListing, mapListings, selectedHasCoordinates, mapModalListing, passing, excluded, reviewQueue,
    reviewedListings, followUps, triageCounts, statusCounts, filterableListings, availableSources,
    availablePostcodes, availableEpc, availableBenefits, displayList, nChecked, comparisonListings,
    withoutCoordinates, activeFilterCount, advancedFilterCount, sqmRange, priceRange, scoreRange,
    yearRange, WORKFLOW_STATUSES, ALL_EPC, clearFilters, removeSingleChipFilter, toggleCheck,
    selectAll, deselectAll, removeComparison, openMapDetail,
  }
}
