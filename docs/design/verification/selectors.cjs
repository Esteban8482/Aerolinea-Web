const { chromium } = require('playwright')
const assert = require('assert')
;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto('http://localhost:5173/registro')
  const group = page.getByRole('group', { name: /nacimiento/i })
  const country = group.getByLabel('País', { exact: true })
  await country.click()
  const search = page.getByRole('combobox', { name: 'Buscar país' })
  await search.fill('Colombia')
  await page.getByRole('option', { name: 'Colombia', exact: true }).waitFor()
  await search.press('ArrowDown')
  await search.press('Enter')
  assert((await country.textContent()).includes('Colombia'))
  const subdivision = group.getByLabel('División territorial', { exact: true })
  await subdivision.click()
  await page.locator('input[role=combobox]').fill('Risaralda')
  await page.getByRole('option', { name: 'Risaralda', exact: true }).click()
  const city = group.getByLabel('Ciudad', { exact: true })
  await city.click()
  await page.locator('input[role=combobox]').fill('Pereira')
  await page
    .getByRole('option', { name: 'Pereira, Risaralda, Colombia', exact: true })
    .click()
  await country.click()
  await page.locator('input[role=combobox]').fill('Argentina')
  await page.getByRole('option', { name: 'Argentina', exact: true }).click()
  assert(!(await subdivision.textContent()).includes('Risaralda'))
  assert(!(await city.textContent()).includes('Pereira'))
  assert(await city.isDisabled())
  // Controlled failures/stale pages exercise shared UI without modifying server data.
  let fail = true
  const queries = []
  await page.route('**/api/v1/reference/countries/**', async (route) => {
    const url = new URL(route.request().url())
    const q = url.searchParams.get('q') || ''
    queries.push(q)
    if (fail) {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Controlled test error' }),
      })
      return
    }
    if (q === 'old') await new Promise((r) => setTimeout(r, 700))
    const results =
      q === 'empty'
        ? []
        : [
            {
              id: q === 'old' ? 901 : 902,
              name: q === 'old' ? 'Old response' : 'Current response',
            },
          ]
    if (url.searchParams.has('page'))
      results[0] = { id: 903, name: 'Second page' }
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        results,
        count: results.length,
        next:
          q === '' && !url.searchParams.has('page')
            ? 'http://localhost:8000/api/v1/reference/countries/?page=2'
            : null,
      }),
    })
  })
  await country.click()
  await page.getByRole('button', { name: 'Reintentar', exact: true }).waitFor()
  fail = false
  await page.getByRole('button', { name: 'Reintentar', exact: true }).click()
  await page.getByRole('option', { name: 'Current response' }).waitFor()
  await page.getByRole('button', { name: 'Cargar más opciones' }).click()
  await page.getByRole('option', { name: 'Second page' }).waitFor()
  await page.locator('input[role=combobox]').fill('old')
  await page.waitForTimeout(300)
  await page.locator('input[role=combobox]').fill('new')
  await page.waitForTimeout(800)
  assert.equal(
    await page.getByRole('option', { name: 'Old response' }).count(),
    0,
  )
  await page.getByRole('option', { name: 'Current response' }).waitFor()
  await page.locator('input[role=combobox]').fill('empty')
  await page
    .getByText('No hay opciones disponibles.', { exact: true })
    .waitFor()
  await page.locator('input[role=combobox]').press('Escape')
  assert(await country.evaluate((x) => x === document.activeElement))
  await page.screenshot({
    path: 'docs/design/implementation-screenshots/selectors-mobile.png',
    fullPage: true,
  })
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth,
  )
  assert(!overflow)
  console.log(
    JSON.stringify({
      realGeography: true,
      dependentReset: true,
      keyboard: true,
      retry: true,
      pagination: true,
      staleProtection: true,
      empty: true,
      overflow,
      errors,
      queries,
    }),
  )
  await browser.close()
})().catch((e) => {
  console.error(e)
  process.exit(1)
})
