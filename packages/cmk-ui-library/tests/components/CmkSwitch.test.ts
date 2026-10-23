/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'
import { h } from 'vue'

test('switch is keyboard focusable and toggles via Space/Enter', async () => {
  const user = userEvent.setup()
  render(CmkSwitch, { props: { modelValue: false } })

  screen.getByRole('switch', { checked: false })

  await user.tab()

  await user.keyboard('[Enter]')

  screen.getByRole('switch', { checked: true })

  await user.keyboard('[Space]')

  screen.getByRole('switch', { checked: false })
})

test('switch takes its accessible name from aria-label', () => {
  render(CmkSwitch, { props: { modelValue: false, ariaLabel: 'Use color' } })

  screen.getByRole('switch', { name: 'Use color' })
})

test('switch takes its accessible name from aria-labelledby', () => {
  render(() => [
    h('span', { id: 'caption' }, 'Use color'),
    h(CmkSwitch, { ariaLabelledby: 'caption' })
  ])

  screen.getByRole('switch', { name: 'Use color' })
})
