const { chromium } = require('playwright')
const fs = require('fs')
const assert = require('assert')
;(async () => {
  const b = await chromium.launch()
  const results = []
  for (const email of ['cliente@alas.com', 'admin@alas.com']) {
    const p = await b.newPage()
    await p.goto('http://localhost:5173/login')
    const line = fs
      .readFileSync('README.md', 'utf8')
      .split('\n')
      .find((x) => x.includes(email) && x.includes('|'))
    const pass = [...line.matchAll(/`([^`]+)`/g)][1][1]
    await p.getByLabel('Correo electrónico').fill(email)
    await p.getByLabel('Contraseña', { exact: true }).fill(pass)
    await p.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
    await p.getByRole('button', { name: 'Cerrar sesión' }).waitFor()
    await p.reload()
    await p.getByRole('button', { name: 'Cerrar sesión' }).waitFor()
    let release, arrived
    const gate = new Promise((r) => (release = r))
    const pending = new Promise((r) => (arrived = r))
    let held = false
    await p.route('**/api/v1/auth/session/', async (route) => {
      if (held) return route.continue()
      held = true
      const response = await route.fetch()
      assert((await response.json()).authenticated)
      arrived()
      await gate
      await route.fulfill({ response })
    })
    await p.evaluate(() => window.dispatchEvent(new Event('focus')))
    await pending
    const logout = p.waitForResponse((r) => r.url().endsWith('/auth/logout/'))
    await p.getByRole('button', { name: 'Cerrar sesión' }).click()
    assert.equal((await logout).status(), 200)
    release()
    await p.waitForTimeout(500)
    await p.getByRole('link', { name: 'Iniciar sesión', exact: true }).waitFor()
    const state = await p.evaluate(() =>
      fetch('/api/v1/auth/session/').then((r) => r.json()),
    )
    assert.equal(state.authenticated, false)
    results.push({
      email,
      login: true,
      reload: true,
      logout: 200,
      lateSessionIgnored: true,
      serverAnonymous: true,
    })
    await p.close()
  }
  console.log(JSON.stringify(results, null, 2))
  await b.close()
})().catch((e) => {
  console.error(e)
  process.exit(1)
})
