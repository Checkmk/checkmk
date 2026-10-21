/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { nextTick } from 'vue'

import AiDockPanel, { type AiDockPanelDock } from '@/ai/components/AiDockPanel.vue'

const slots = { default: '<div>Pane content</div>' }

async function focusedSeparator(): Promise<HTMLElement> {
  const separator = screen.getByRole('separator')
  await userEvent.pointer({ keys: '[MouseLeft]', target: separator })
  return separator
}

function dockIntoContainerOfWidth(width: number): void {
  const container = document.createElement('div')
  vi.spyOn(container, 'getBoundingClientRect').mockReturnValue(
    DOMRect.fromRect({ width, height: 400 })
  )
  vi.spyOn(HTMLElement.prototype, 'offsetParent', 'get').mockReturnValue(container)
  onTestFinished(() => {
    vi.restoreAllMocks()
  })
}

test.each<{ dock: AiDockPanelDock; key: string }>([
  { dock: 'right', key: '{ArrowLeft}' },
  { dock: 'left', key: '{ArrowRight}' },
  { dock: 'bottom', key: '{ArrowUp}' }
])('docked $dock, $key grows the pane away from its edge', async ({ dock, key }) => {
  render(AiDockPanel, { props: { dock, size: 300, minSize: 200 }, slots })

  await focusedSeparator()
  await userEvent.keyboard(key)

  expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow', '350')
})

test.each<{ dock: AiDockPanelDock; key: string }>([
  { dock: 'right', key: '{ArrowRight}' },
  { dock: 'left', key: '{ArrowLeft}' },
  { dock: 'bottom', key: '{ArrowDown}' }
])('docked $dock, $key shrinks the pane towards its edge', async ({ dock, key }) => {
  render(AiDockPanel, { props: { dock, size: 400, minSize: 200 }, slots })

  await focusedSeparator()
  await userEvent.keyboard(key)

  expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow', '350')
})

test('the separator lies across the pane when docked at the bottom', () => {
  render(AiDockPanel, { props: { dock: 'bottom', size: 300, minSize: 200 }, slots })

  expect(screen.getByRole('separator')).toHaveAttribute('aria-orientation', 'horizontal')
})

test('never grows beyond the element it docks into', async () => {
  dockIntoContainerOfWidth(500)
  render(AiDockPanel, { props: { size: 480, minSize: 200 }, slots })
  await nextTick()

  await focusedSeparator()
  await userEvent.keyboard('{ArrowLeft}')

  expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow', '500')
})

test('a size beyond the element it docks into shrinks to fit it', async () => {
  dockIntoContainerOfWidth(500)

  render(AiDockPanel, { props: { size: 800, minSize: 200 }, slots })
  await nextTick()

  expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow', '500')
})

test('dragging the handle away from the edge grows the pane by the distance moved', async () => {
  render(AiDockPanel, { props: { size: 300, minSize: 200 }, slots })
  const separator = screen.getByRole('separator')

  await userEvent.pointer([
    { keys: '[MouseLeft>]', target: separator, coords: { clientX: 700 } },
    { target: separator, coords: { clientX: 580 } },
    { keys: '[/MouseLeft]', target: separator }
  ])

  expect(separator).toHaveAttribute('aria-valuenow', '420')
})

test('dragging the handle below half of the minimum size collapses the pane', async () => {
  render(AiDockPanel, { props: { size: 300, minSize: 200 }, slots })
  const separator = screen.getByRole('separator')

  await userEvent.pointer([
    { keys: '[MouseLeft>]', target: separator, coords: { clientX: 700 } },
    { target: separator, coords: { clientX: 950 } },
    { keys: '[/MouseLeft]', target: separator }
  ])

  expect(screen.getByText('Pane content')).not.toBeVisible()
})

test('a drag ends when the handle loses the pointer', async () => {
  render(AiDockPanel, { props: { size: 300, minSize: 200 }, slots })
  const separator = screen.getByRole('separator')
  await userEvent.pointer([
    { keys: '[MouseLeft>]', target: separator, coords: { clientX: 700 } },
    { target: separator, coords: { clientX: 950 } }
  ])

  await fireEvent.lostPointerCapture(separator, { pointerId: 1 })
  await userEvent.pointer([
    { keys: '[/MouseLeft]', target: document.body },
    { target: separator, coords: { clientX: 600 } }
  ])

  expect(screen.getByText('Pane content')).not.toBeVisible()
})

test('Enter collapses the pane', async () => {
  render(AiDockPanel, { props: { size: 300, minSize: 200 }, slots })
  await focusedSeparator()

  await userEvent.keyboard('{Enter}')

  expect(screen.getByText('Pane content')).not.toBeVisible()
})

test('hides the handle while collapsed', () => {
  render(AiDockPanel, { props: { size: 300, minSize: 200, collapsed: true }, slots })

  expect(screen.queryByRole('separator')).not.toBeInTheDocument()
})
