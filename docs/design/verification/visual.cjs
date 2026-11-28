const { chromium } = require('playwright')
const fs = require('fs')
;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text())
  })
  const dir = process.cwd() + '/docs/design/implementation-screenshots'
  fs.mkdirSync(dir, { recursive: true })
  const report = []
  for (const [name, width, height] of [
    ['desktop', 1440, 1000],
    ['tablet', 768, 1024],
    ['mobile', 390, 844],
  ]) {
    await page.setViewportSize({ width, height })
    for (const [screen, path] of [
      ['login', '/login'],
      ['recovery', '/login'],
      ['verify-email', '/verificar'],
      ['reset-password', '/restablecer#token=visual-test-only'],
    ]) {
      await page.goto('http://localhost:5173' + path)
      await page.getByRole('heading', { level: 1 }).waitFor()
      if (screen === 'recovery')
        await page
          .getByRole('button', { name: '¿Olvidaste tu contraseña?' })
          .click()
      await page.screenshot({
        path: `${dir}/${screen}-${name}.png`,
        fullPage: true,
      })
      report.push({
        screen,
        viewport: name,
        ...(await page.evaluate(() => ({
          width: innerWidth,
          scrollWidth: document.documentElement.scrollWidth,
          duplicateLabels: [
            ...document.querySelectorAll('input,select'),
          ].filter((x) => x.labels?.length > 1).length,
        }))),
      })
    }
  }
  console.log(JSON.stringify({ report, errors }, null, 2))
  await browser.close()
})().catch((e) => {
  console.error(e)
  process.exit(1)
})
