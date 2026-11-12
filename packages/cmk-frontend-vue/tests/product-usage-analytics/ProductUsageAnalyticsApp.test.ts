/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { afterEach, expect, test } from 'vitest'

import ProductUsageAnalyticsApp from '@/product-usage-analytics/ProductUsageAnalyticsApp.vue'

const SETTING = '/objects/global_setting/{varname}'

const ENABLED_CHOICE_ID = 'id-of-enabled'

const STORED_VALUE = {
  enabled: 'id-of-not-decided',
  proxy_setting: ['global', 'corporate_proxy']
}

let saved: Array<{ ifMatch: string | null; value: unknown }> = []

const server = useMswServer(
  restApiHttp.get(SETTING, ({ response }) =>
    response(200).json(
      {
        varname: 'product_usage_analytics',
        value: STORED_VALUE,
        spec: {},
        origin: 'global'
      },
      { headers: { ETag: '"v1"' } }
    )
  ),
  restApiHttp.put(SETTING, async ({ request, response }) => {
    const body = await request.json()
    saved.push({ ifMatch: request.headers.get('If-Match'), value: body.value })
    return response(200).json(
      {
        varname: 'product_usage_analytics',
        value: body.value,
        spec: {},
        origin: 'global'
      },
      { headers: { ETag: '"v2"' } }
    )
  })
)

const REMINDER_COOKIE = 'product_usage_analytics_popup_timestamp'

afterEach(() => {
  saved = []
  document.cookie = `${REMINDER_COOKIE}=; path=/; max-age=0`
})

function renderPopup() {
  render(ProductUsageAnalyticsApp, {
    props: {
      // Hash links: jsdom does not implement navigating to another page.
      global_settings_link: '#global-settings',
      manifest_link: 'https://analytics.checkmk.com/manifest',
      enabled_choice_id: ENABLED_CHOICE_ID,
      activate_changes_link: '#activate-changes',
      reminder_cookie: { name: REMINDER_COOKIE, path: '/', max_age_seconds: 3600 }
    }
  })
}

function reminderCookie(): string | undefined {
  return document.cookie.split('; ').find((cookie) => cookie.startsWith(`${REMINDER_COOKIE}=`))
}

test('enabling stores the choice and keeps the proxy setting', async () => {
  renderPopup()

  await userEvent.click(
    await screen.findByRole('button', { name: 'Enable product usage analytics' })
  )
  await screen.findByRole('button', { name: 'Close' })

  expect(saved).toEqual([
    {
      ifMatch: '"v1"',
      value: { enabled: ENABLED_CHOICE_ID, proxy_setting: ['global', 'corporate_proxy'] }
    }
  ])
})

test('after enabling, the pop-up leads to the pending changes', async () => {
  renderPopup()

  await userEvent.click(
    await screen.findByRole('button', { name: 'Enable product usage analytics' })
  )
  await userEvent.click(await screen.findByRole('button', { name: 'Activate changes' }))

  expect(window.location.hash).toBe('#activate-changes')
})

test('a rejected save tells the user that product usage analytics is not enabled', async () => {
  server.use(
    restApiHttp.put(SETTING, ({ response }) =>
      response.untyped(
        HttpResponse.json(
          { title: 'Precondition failed', detail: 'ETag mismatch' },
          { status: 412 }
        )
      )
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
