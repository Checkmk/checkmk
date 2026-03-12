/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import ResponsiveGridWidgetButton from '@/dashboard/components/ResponsiveGrid/ResponsiveGridWidgetButton.vue'

test('renders a button element', () => {
  render(ResponsiveGridWidgetButton, {
    props: { iconName: 'db-widget-edit', title: 'Edit widget' }
  })

  expect(screen.getByRole('button')).toBeInTheDocument()
})

test('emits click event on button click', async () => {
  const { emitted } = render(ResponsiveGridWidgetButton, {
    props: { iconName: 'db-widget-edit', title: 'Edit widget' }
  })

  await fireEvent.click(screen.getByRole('button'))

  expect(emitted()['click']).toHaveLength(1)
})

test('does not submit form due to .prevent modifier', async () => {
  const testComponent = defineComponent({
    components: { ResponsiveGridWidgetButton },
    template: `
      <form aria-label="test">
        <ResponsiveGridWidgetButton icon-name="db-widget-edit" title="Edit widget" />
      </form>
    `
  })
  render(testComponent)

  const submitHandler = vi.fn((e: Event) => e.preventDefault())
  screen.getByRole('form').addEventListener('submit', submitHandler)
  await fireEvent.click(screen.getByRole('button'))

  expect(submitHandler).not.toHaveBeenCalled()
})
