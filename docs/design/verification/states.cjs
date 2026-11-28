const { chromium } = require('playwright')
const assert = require('assert')
;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
  let verifies = 0
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.route('**/api/v1/auth/verify-email/', async (r) => {
    verifies++
    await new Promise((done) => setTimeout(done, 400))
    await r.fulfill({ json: { message: 'verified' } })
  })
  await page.goto(
    'http://localhost:5173/verificar#token=synthetic-browser-test',
  )
  await page
    .getByRole('heading', { name: 'Correo verificado', exact: true })
    .waitFor()
  assert.equal(verifies, 1)
  assert(!page.url().includes('#'))
  await page.screenshot({
    path: 'docs/design/implementation-screenshots/verify-success-mobile.png',
  })
  await page.route('**/api/v1/auth/password-reset/', (r) =>
    r.fulfill({ json: { message: 'reset' } }),
  )
  await page.goto(
    'http://localhost:5173/restablecer#token=synthetic-browser-test',
  )
  await page
    .getByLabel('Nueva contraseña', { exact: true })
    .fill('Synthetic-Password-For-Test!')
  await page
    .getByLabel('Confirmar nueva contraseña', { exact: true })
    .fill('Mismatch-For-Test!')
  await page.getByRole('button', { name: 'Guardar contraseña' }).click()
  await page.getByRole('alert').filter({ hasText: 'no coinciden' }).waitFor()
  await page
    .getByLabel('Confirmar nueva contraseña', { exact: true })
    .fill('Synthetic-Password-For-Test!')
  await page.getByRole('button', { name: 'Guardar contraseña' }).click()
  await page.getByRole('heading', { name: 'Contraseña actualizada' }).waitFor()
  assert(!page.url().includes('#'))
  await page.goto('http://localhost:5173/login')
  await page.getByRole('button', { name: '¿Olvidaste tu contraseña?' }).click()
  await page
    .getByLabel('Correo electrónico', { exact: true })
    .fill('milestone1-nonexistent-browser-check@example.invalid')
  const response = page.waitForResponse((r) =>
    r.url().endsWith('/auth/password-recovery/'),
  )
  await page.getByRole('button', { name: 'Enviar instrucciones' }).click()
  assert.equal((await response).status(), 202)
  await page
    .getByRole('status')
    .filter({ hasText: 'Si la cuenta existe' })
    .waitFor()
  const layouts = []
  for (const path of ['/', '/vuelos', '/registro', '/check-in']) {
    await page.goto('http://localhost:5173' + path)
    await page.waitForTimeout(700)
    layouts.push({
      path,
      ...(await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth,
        missingLabels: [
          ...document.querySelectorAll('input:not([type=hidden]),select'),
        ].filter((x) => !x.labels?.length && !x.getAttribute('aria-label'))
          .length,
      }))),
    })
  }
  await page.goto('http://localhost:5173/vuelos')
  const origin = page.getByLabel('Ciudad de origen', { exact: true }).first()
  await origin.click()
  await page.getByRole('option').first().waitFor()
  const choice = await page.getByRole('option').first().textContent()
  await page.getByRole('option').first().click()
  assert((await origin.textContent()).includes(choice))
  await page.screenshot({
    path: 'docs/design/implementation-screenshots/commercial-selector-mobile.png',
    fullPage: true,
  })
  console.log(
    JSON.stringify(
      {
        mockedVerifySuccess: true,
        singleVerificationPost: verifies,
        mockedResetSuccess: true,
        confirmationValidation: true,
        realRecoveryNonexistent: 202,
        commercialSelector: true,
        layouts,
        errors,
      },
      null,
      2,
    ),
  )
  await browser.close()
})().catch((e) => {
  console.error(e)
  process.exit(1)
})
