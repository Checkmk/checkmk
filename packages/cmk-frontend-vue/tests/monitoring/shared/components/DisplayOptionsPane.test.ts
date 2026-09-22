/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import DisplayOptionsPane from '@/monitoring/shared/components/DisplayOptionsPane.vue'
import type { DisplayOptions } from '@/monitoring/shared/types'

const MODEL_VALUE: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'mixed' }

test('picking a date format closes its dropdown', async () => {
  render(DisplayOptionsPane, { props: { modelValue: MODEL_VALUE } })

  await userEvent.click(screen.getByRole('combobox', { name: 'Date format' }))
  await userEvent.click(screen.getByRole('option', { name: '18.12.1970' }))

  expect(screen.queryAllByRole('option')).toHaveLength(0)
})

test('picking a timestamp format closes its dropdown', async () => {
  render(DisplayOptionsPane, { props: { modelValue: MODEL_VALUE } })

  await userEvent.click(screen.getByRole('combobox', { name: 'Timestamp format' }))
  await userEvent.click(screen.getByRole('option', { name: 'Absolute' }))

  expect(screen.queryAllByRole('option')).toHaveLength(0)
})
