/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import MonitoringLegacyViewButton from '@/monitoring/shared/components/MonitoringLegacyViewButton.vue'

const PROPS = { url: 'view.py?view_name=allhosts', title: 'Return to classic view' }

test('navigates to the legacy view on click', async () => {
  const assign = vi.fn()
  vi.stubGlobal('location', {
    set href(url: string) {
      assign(url)
    }
  })

  render(MonitoringLegacyViewButton, { props: PROPS })
  await userEvent.click(screen.getByRole('button', { name: /classic view/ }))

  expect(assign).toHaveBeenCalledWith(PROPS.url)
})

test('keeps the full title as tooltip for when the text is collapsed on small screens', () => {
  render(MonitoringLegacyViewButton, { props: PROPS })

  expect(screen.getByRole('button', { name: /classic view/ })).toHaveAttribute('title', PROPS.title)
})
