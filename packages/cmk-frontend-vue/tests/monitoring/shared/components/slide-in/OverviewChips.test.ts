/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'

const ITEMS = [{ text: 'linux' as TranslatedString }]

test('emits the entry clicked on', async () => {
  const { emitted } = render(OverviewChips, {
    props: { items: ITEMS, action: { title: () => 'Filter by linux' as TranslatedString } }
  })

  await userEvent.click(screen.getByRole('button', { name: 'linux' }))

  expect(emitted('select')).toStrictEqual([[ITEMS[0]]])
})

test('keeps the entries plain without an action', () => {
  render(OverviewChips, { props: { items: ITEMS } })

  expect(screen.queryByRole('button', { name: 'linux' })).not.toBeInTheDocument()
})
