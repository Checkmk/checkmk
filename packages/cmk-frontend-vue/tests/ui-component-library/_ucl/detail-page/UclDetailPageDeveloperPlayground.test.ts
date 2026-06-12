/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import UclDetailPageDeveloperPlayground from '@ucl/_ucl/components/detail-page/UclDetailPageDeveloperPlayground.vue'

test('renders section heading', () => {
  render(UclDetailPageDeveloperPlayground)
  screen.getByText('Developer Playground')
})

test('expands its content region when the playground header is clicked', async () => {
  render(UclDetailPageDeveloperPlayground, {
    slots: { default: '<div data-testid="playground-body">playground controls</div>' }
  })

  // The default-slot content is wrapped in the accordion's collapsible content
  // region. It starts collapsed (data-state="closed").
  const region = screen.getByRole('region', { hidden: true })
  expect(region).toHaveAttribute('data-state', 'closed')

  await fireEvent.click(screen.getByText('Developer Playground'))

  // Clicking the header expands the region that holds the slotted content.
  expect(region).toHaveAttribute('data-state', 'open')
})
