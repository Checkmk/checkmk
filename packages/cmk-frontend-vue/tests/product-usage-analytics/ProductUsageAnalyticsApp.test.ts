/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import ProductUsageAnalyticsApp from '@/product-usage-analytics/ProductUsageAnalyticsApp.vue'

import { useMswServer } from '@tests/vitest.msw'

const ENABLE = 'ajax_enable_product_usage_analytics.py'

const CSRF_TOKEN = 'the-csrf-token'

let enableRequests: string[] = []

const server = useMswServer(
  http.post(ENABLE, async ({ request }) => {
    enableRequests.push(new URLSearchParams(await request.text()).get('request') ?? '')
    return HttpResponse.json({ result_code: 0, result: {}, severity: 'success' })
  })
)

const REMINDER_COOKIE = 'product_usage_analytics_popup_timestamp'

beforeEach(() => {
  vi.stubGlobal('global_csrf_token', CSRF_TOKEN)
})

afterEach(() => {
  enableRequests = []
  vi.unstubAllGlobals()
  document.cookie = `${REMINDER_COOKIE}=; path=/; max-age=0`
})

function renderPopup() {
  render(ProductUsageAnalyticsApp, {
    props: {
      // Hash links: jsdom does not implement navigating to another page.
      global_settings_link: '#global-settings',
      manifest_link: 'https://analytics.checkmk.com/manifest',
      activate_changes_link: '#activate-changes',
      reminder_cookie: { name: REMINDER_COOKIE, path: '/', max_age_seconds: 3600 }
    }
  })
}

function reminderCookie(): string | undefined {
  return document.cookie.split('; ').find((cookie) => cookie.startsWith(`${REMINDER_COOKIE}=`))
}

test('enabling sends one request with the CSRF token', async () => {
  renderPopup()

  await userEvent.click(
    await screen.findByRole('button', { name: 'Enable product usage analytics' })
  )
  await screen.findByRole('button', { name: 'Close' })

  expect(enableRequests).toEqual([JSON.stringify({ _csrf_token: CSRF_TOKEN })])
})

test('after enabling, the pop-up leads to the pending changes', async () => {
  renderPopup()

  await userEvent.click(
    await screen.findByRole('button', { name: 'Enable product usage analytics' })
  )
  const link = await screen.findByRole('link', { name: 'Activate changes' })

  expect(link).toHaveAttribute('href', '#activate-changes')
  expect(link).toHaveAttribute('target', 'main')
})

test('a rejected save tells the user that product usage analytics is not enabled', async () => {
  server.use(
    http.post(ENABLE, () =>
      HttpResponse.json({
        result_code: 1,
        result: 'You are not permitted to enable product usage analytics.',
        severity: 'error'
      })
    )
  )
  renderPopup()

  await userEvent.click(
    await screen.findByRole('button', { name: 'Enable product usage analytics' })
  )

  expect(
    await screen.findByText(/Product usage analytics could not be enabled/)
  ).toBeInTheDocument()
})

test('the manifest opens in a new tab', async () => {
  renderPopup()

  const link = await screen.findByRole('link', { name: 'manifest' })

  expect(link).toHaveAttribute('href', 'https://analytics.checkmk.com/manifest')
  expect(link).toHaveAttribute('target', '_blank')
})

test.each([
  { role: 'button', name: 'Remind me again in 30 days' },
  { role: 'link', name: 'global settings' }
])('"$name" postpones the next reminder', async ({ role, name }) => {
  renderPopup()

  await userEvent.click(await screen.findByRole(role, { name }))

  expect(reminderCookie()).toMatch(new RegExp(`^${REMINDER_COOKIE}=\\d+`))
})

test('showing the pop-up does not postpone the next reminder', async () => {
  renderPopup()

  await screen.findByRole('button', { name: 'Enable product usage analytics' })

  expect(reminderCookie()).toBeUndefined()
})
