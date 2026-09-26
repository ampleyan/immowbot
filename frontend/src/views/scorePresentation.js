export const SCORE_BANDS = [
  { key: 'strong', label: 'Strong match', shortLabel: 'Strong', min: 75, color: '#027A48', cardClass: 'pill-green' },
  { key: 'worth-a-look', label: 'Worth a look', shortLabel: 'Worth a look', min: 55, color: '#B54708', cardClass: 'pill-yellow' },
  { key: 'review', label: 'Review carefully', shortLabel: 'Review', min: -Infinity, color: '#C01048', cardClass: 'pill-red' },
]

const SCORE_COMPONENT_LABELS = {
  price: 'Price',
  surface_area: 'Surface area',
  bedrooms: 'Bedrooms',
  epc: 'EPC',
  completeness: 'Listing completeness',
  outdoor: 'Outdoor space',
  parking: 'Parking',
  price_per_sqm: 'Price per m²',
  price_reduced: 'Price reduction',
  days_on_market: 'Days tracked',
  tenant: 'Current tenant',
  monthly_charges: 'Monthly charges',
  yield: 'Rental yield',
}

export function scoreBand(score) {
  if (score === null || score === undefined || !Number.isFinite(Number(score))) return null
  return SCORE_BANDS.find(band => Math.round(Number(score)) >= band.min) || SCORE_BANDS[SCORE_BANDS.length - 1]
}

export function scoreColor(score) {
  return scoreBand(score)?.color || '#667085'
}

export function scoreCardClass(score) {
  return scoreBand(score)?.cardClass || 'pill-neutral'
}

export function scoreComponentRows(listing) {
  const components = listing?._components || {}
  const rows = Object.entries(SCORE_COMPONENT_LABELS)
    .filter(([key]) => Object.hasOwn(components, key))
    .map(([key, label]) => ({ key, label, points: Number(components[key]) || 0 }))

  // The backend omits zero-valued score parts. Keep this contributor visible
  // whenever its first-seen date exists, so the explanation matches the score.
  if (!Object.hasOwn(components, 'days_on_market') && listing?._first_seen_at) {
    rows.push({ key: 'days_on_market', label: SCORE_COMPONENT_LABELS.days_on_market, points: 0 })
  }

  return rows
}

export function formatScorePoints(value) {
  const points = Number(value) || 0
  const formatted = Number.isInteger(points) ? String(points) : points.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
  return `${points > 0 ? '+' : ''}${formatted} pts`
}
