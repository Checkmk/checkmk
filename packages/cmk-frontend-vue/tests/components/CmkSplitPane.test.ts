/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'

import CmkSplitPane from '@/components/CmkSplitPane.vue'

const slots = {
  left: '<div>Left content</div>',
  right: '<div>Right content</div>'
}

test('renders both panes', async () => {
  render(CmkSplitPane, { slots })

  await screen.findByText('Left content')
  await screen.findByText('Right content')
})

test('exposes an accessible resize handle', async () => {
  render(CmkSplitPane, { slots })

  const separator = await screen.findByRole('separator')
  expect(separator).toHaveAttribute('aria-valuenow')
})

test('collapses the right pane when collapsed is set', async () => {
  const { rerender } = render(CmkSplitPane, {
    props: { collapsed: false, rightDefaultSize: 30 },
    slots
  })

  const separator = await screen.findByRole('separator')
  expect(separator.getAttribute('aria-valuenow')).toBe('70')

  await rerender({ collapsed: true })

  await waitFor(() => {
    expect(separator.getAttribute('aria-valuenow')).toBe('100')
  })
})

test('resizes with the keyboard once the handle is focused via pointer', async () => {
  const user = userEvent.setup()
  render(CmkSplitPane, { props: { rightDefaultSize: 30, keyboardResizeBy: 10 }, slots })

  const separator = await screen.findByRole('separator')
  expect(separator.getAttribute('aria-valuenow')).toBe('70')

  await user.pointer({ keys: '[MouseLeft]', target: separator })
  expect(document.activeElement).toBe(separator)

  await user.keyboard('{ArrowLeft}')
  expect(separator.getAttribute('aria-valuenow')).toBe('60')

  await user.keyboard('{ArrowRight}{ArrowRight}')
  expect(separator.getAttribute('aria-valuenow')).toBe('80')
})

test('hides the handle while collapsed by default', async () => {
  render(CmkSplitPane, { props: { collapsed: true }, slots })

  await waitFor(() => {
    expect(screen.queryByRole('separator')).not.toBeInTheDocument()
  })
})

test('keeps the handle visible while collapsed when opted out', async () => {
  render(CmkSplitPane, {
    props: { collapsed: true, hideHandleWhenCollapsed: false },
    slots
  })

  await screen.findByRole('separator')
})
