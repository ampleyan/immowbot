import { expect, test } from '@playwright/test'

const publishedAt = new Date(Date.now() - 8 * 86_400_000).toISOString()
const trackedAt = new Date(Date.now() - 11 * 86_400_000).toISOString()
const longDescription = `${'Well-maintained property with bright rooms. '.repeat(36)}COMPLETE-LISTING-END`

const listings = [
  {
    url: 'https://example.test/listing/strong',
    source: 'immoweb',
    source_listing_id: 'e2e-strong',
    address: '8 Test Street',
    city: 'Antwerp',
    postcode: '2000',
    latitude: 51.2213,
    longitude: 4.3997,
    property_type: 'house',
    price: 280000,
    surface_area: 120,
    bedrooms: 3,
    epc_score: 'B',
    source_created_at: publishedAt,
    _first_seen_at: trackedAt,
    description: longDescription,
    _score: 74.6,
    _score_weights: { price: 30, surface_area: 25, bedrooms: 15, epc: 20, completeness: 10 },
    _components: {
      price: 15,
      surface_area: 15,
      bedrooms: 10,
      epc: 15,
      completeness: 9.6,
      outdoor: 5,
      parking: 5,
      price_per_sqm: 5,
      price_reduced: 5,
      days_on_market: 5,
      tenant: -10,
      monthly_charges: -5,
    },
    _workflow: { status: 'New', rating: null },
    all_property_details: { Garage: true },
  },
  {
    url: 'https://example.test/listing/unknown-age',
    source: 'immoweb',
    source_listing_id: 'e2e-unknown-age',
    address: '3 Sample Road',
    city: 'Antwerp',
    postcode: '2018',
    latitude: 51.219,
    longitude: 4.41,
    property_type: 'apartment',
    price: 215000,
    surface_area: 78,
    bedrooms: 2,
    epc_score: 'C',
    source_created_at: 'not-a-date',
    _first_seen_at: 'also-not-a-date',
    _score: 54.5,
    _components: { price: 20, epc: 14, completeness: 20.5 },
    _workflow: { status: 'New', rating: null },
  },
]

async function openApp(page, viewport, theme = 'default') {
  await page.addInitScript(value => localStorage.setItem('theme', value), theme)
  await page.setViewportSize(viewport)
  await page.route('**/api/**', async route => {
    const pathname = new URL(route.request().url()).pathname
    if (pathname === '/api/runs/stream') return route.abort()
    if (pathname === '/api/auth/me') return route.fulfill({ json: { id: 7, username: 'e2e', is_admin: true } })
    if (pathname === '/api/health') return route.fulfill({ json: { version: 'e2e' } })
    if (pathname === '/api/listings') return route.fulfill({ json: listings })
    if (pathname === '/api/lists' || pathname === '/api/alerts') return route.fulfill({ json: [] })
    if (/\/api\/changes\//.test(pathname)) return route.fulfill({ json: { changes: [] } })
    if (/\/api\/workflow\//.test(pathname)) return route.fulfill({ json: { status: 'New', rating: null } })
    if (/\/api\/interactions\//.test(pathname)) return route.fulfill({ json: [] })
    return route.fulfill({ json: {} })
  })
  await page.goto('/active')
  await expect(page.getByLabel('Search listings')).toBeVisible()
  await expect(page.locator('.card')).toHaveCount(2)
}

test('iPhone detail keeps score, dates, controls, and full description accessible', async ({ page }, testInfo) => {
  await openApp(page, { width: 390, height: 844 })

  const firstCard = page.locator('.card').filter({ hasText: '8 Test Street' })
  await expect(firstCard.getByRole('checkbox', { name: 'Select 8 Test Street, Antwerp, 2000' })).toBeVisible()
  await expect(firstCard.getByText('Strong', { exact: true })).toBeVisible()
  await expect(firstCard.getByText('75', { exact: true })).toBeVisible()
  await expect(firstCard.getByText(/On market 8 days/)).toBeVisible()
  await firstCard.getByRole('button', { name: 'Add property note' }).click()
  await expect(firstCard.getByLabel('Note for 8 Test Street, Antwerp, 2000')).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await firstCard.getByRole('button', { name: 'Close property note' }).click()

  const unknownAgeCard = page.locator('.card').filter({ hasText: '3 Sample Road' })
  await expect(unknownAgeCard.locator('.card-id')).not.toContainText(/On market|Tracked|0 days/)
  await expect(unknownAgeCard.getByText('Worth a look')).toBeVisible()

  const detailsButton = firstCard.getByRole('button', { name: 'View details for 8 Test Street, Antwerp, 2000' })
  await detailsButton.click()
  const dialog = page.getByRole('dialog', { name: 'Property details: 8 Test Street, Antwerp, 2000' })
  await expect(dialog).toBeVisible()
  await expect(dialog).toHaveAttribute('aria-modal', 'true')
  const dialogBounds = await dialog.boundingBox()
  expect(dialogBounds).toMatchObject({ x: 0, y: 0, width: 390, height: 844 })
  await expect(page.locator('#app')).toHaveAttribute('inert', '')
  await expect(dialog).toContainText('Score 75 / 100 · Strong match')
  for (const label of ['Parking', 'Price per m²', 'Price reduction', 'Days tracked', 'Current tenant', 'Monthly charges']) {
    await expect(dialog.locator('.score-row').filter({ hasText: label })).toHaveCount(1)
  }
  await expect(dialog).toContainText('On market')
  await expect(dialog.getByRole('button', { name: 'Close property details' })).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Mark as interested' })).toHaveAttribute('aria-pressed', 'false')
  await expect(dialog.getByRole('button', { name: 'Show full description' })).toBeVisible()
  const lightThemeContrast = await dialog.locator('.detail-metric-label').first().evaluate(element => {
    const luminance = color => {
      const channels = color.match(/[\d.]+/g).slice(0, 3).map(value => {
        const channel = Number(value) / 255
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    }
    const foreground = luminance(getComputedStyle(element).color)
    const background = luminance(getComputedStyle(element.closest('.detail-metric')).backgroundColor)
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
  })
  expect(lightThemeContrast).toBeGreaterThanOrEqual(4.5)

  const image = await page.screenshot({ animations: 'disabled' })
  await testInfo.attach('iPhone property detail', { body: image, contentType: 'image/png' })

  await dialog.getByRole('button', { name: 'Show full description' }).click()
  await expect(dialog).toContainText('COMPLETE-LISTING-END')
  await dialog.evaluate(element => {
    const focusable = [...element.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')]
      .filter(node => node.getClientRects().length)
    focusable.at(-1)?.focus()
  })
  await page.keyboard.press('Tab')
  await expect(dialog.locator('button:visible, a[href]:visible, input:visible, select:visible, textarea:visible').first()).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(page.locator('#app')).not.toHaveAttribute('inert', '')
  await expect(detailsButton).toBeFocused()
})

test('map uses the same score bands and labels as listings and detail', async ({ page }) => {
  await openApp(page, { width: 1280, height: 900 })
  await page.route('https://*.tile.openstreetmap.org/**', route => route.abort())
  await page.getByRole('button', { name: /Map view/ }).click()
  await expect(page.locator('.leaflet-marker-icon')).toHaveCount(2)
  await page.locator('.leaflet-marker-icon').first().click()
  const popup = page.locator('.leaflet-popup-content .map-popup')
  await expect(popup).toContainText('Strong match')
  await expect(popup).toContainText('Score 75 / 100')
  for (const band of ['Strong match (75+)', 'Worth a look (55–74)', 'Review carefully (below 55)']) {
    await expect(page.locator('.map-legend')).toContainText(band)
  }
})

test('dark theme keeps property score and detail labels readable', async ({ page }, testInfo) => {
  await openApp(page, { width: 390, height: 844 }, 'vlaams')
  const card = page.locator('.card').filter({ hasText: '8 Test Street' })
  await card.getByRole('button', { name: 'View details for 8 Test Street, Antwerp, 2000' }).click()
  const dialog = page.getByRole('dialog', { name: 'Property details: 8 Test Street, Antwerp, 2000' })
  await expect(dialog.locator('.score-tone-strong')).toHaveText('Score 75 / 100 · Strong match')
  const contrast = await dialog.locator('.detail-metric-label').first().evaluate(element => {
    const luminance = color => {
      const channels = color.match(/[\d.]+/g).slice(0, 3).map(value => {
        const channel = Number(value) / 255
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    }
    const foreground = luminance(getComputedStyle(element).color)
    const background = luminance(getComputedStyle(element.closest('.detail-metric')).backgroundColor)
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
  })
  expect(contrast).toBeGreaterThanOrEqual(4.5)
  await expect(dialog.locator('.purchase-estimate')).toHaveCSS('background-color', 'rgb(26, 26, 26)')
  const scoreContrast = await dialog.locator('.score-tone-strong').evaluate(element => {
    const luminance = color => {
      const channels = color.match(/[\d.]+/g).slice(0, 3).map(value => {
        const channel = Number(value) / 255
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    }
    const foreground = luminance(getComputedStyle(element).color)
    const background = luminance(getComputedStyle(element.closest('.detail-panel')).backgroundColor)
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
  })
  expect(scoreContrast).toBeGreaterThanOrEqual(4.5)
  await testInfo.attach('iPhone property detail - Vlaams theme', { body: await page.screenshot({ animations: 'disabled' }), contentType: 'image/png' })
})
