/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'

function renderWithShowTitle(initialShowTitle: boolean) {
  const showTitle = ref(initialShowTitle)
  return render(
    defineComponent({
      setup: () => () =>
        h(WidgetVisualization, {
          title: 'My widget',
          showTitleBackground: false,
          showTitle: showTitle.value,
          'onUpdate:showTitle': (value: boolean) => (showTitle.value = value)
        })
    })
  )
}

describe('WidgetVisualization', () => {
  it('offers the title text and title background when the title is shown', () => {
    renderWithShowTitle(true)

    expect(screen.getByDisplayValue('My widget')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Show title background' })).toBeInTheDocument()
  })

  it('hides the title text and title background when the title is hidden', () => {
    renderWithShowTitle(false)

    expect(screen.queryByDisplayValue('My widget')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('checkbox', { name: 'Show title background' })
    ).not.toBeInTheDocument()
  })

  it('offers the title options once the title is switched on', async () => {
    const user = userEvent.setup()
    renderWithShowTitle(false)

    await user.click(screen.getByRole('checkbox', { name: 'Show title' }))

    expect(screen.getByDisplayValue('My widget')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Show title background' })).toBeInTheDocument()
  })
})
