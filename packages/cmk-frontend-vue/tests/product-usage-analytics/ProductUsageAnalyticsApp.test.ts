/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { afterEach, expect, test } from 'vitest'

import ProductUsageAnalyticsApp from '@/product-usage-analytics/ProductUsageAnalyticsApp.vue'

const REMINDER_COOKIE = 'product_usage_analytics_popup_timestamp'

afterEach(() => {
  document.cookie = `${REMINDER_COOKIE}=; path=/; max-age=0`
})

function renderPopup() {
  render(ProductUsageAnalyticsApp, {
    props: {
      // A hash link: jsdom does not implement navigating to another page.
      global_settings_link: '#global-settings',
      reminder_cookie: { name: REMINDER_COOKIE, path: '/', max_age_seconds: 3600 }
    }
  })
}

function reminderCookie(): string | undefined {
  return document.cookie.split('; ').find((cookie) => cookie.startsWith(`${REMINDER_COOKIE}=`))
}

test.each([
  { role: 'button', name: 'Remind me again in 30 days' },
  { role: 'link', name: 'Manage in global settings' }
])('"$name" postpones the next reminder', async ({ role, name }) => {
  renderPopup()

  await userEvent.click(await screen.findByRole(role, { name }))

  expect(reminderCookie()).toMatch(new RegExp(`^${REMINDER_COOKIE}=\\d+`))
})

test('showing the pop-up does not postpone the next reminder', async () => {
  renderPopup()

  await screen.findByRole('button', { name: 'Remind me again in 30 days' })

  expect(reminderCookie()).toBeUndefined()
})
