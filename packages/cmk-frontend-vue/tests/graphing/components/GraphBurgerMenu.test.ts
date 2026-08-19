/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import GraphBurgerMenu from '@/graphing/components/GraphBurgerMenu.vue'
import type { BurgerMenuGroup } from '@/graphing/types'

const GROUPS: BurgerMenuGroup[] = [
  {
    heading: 'Add to dashboard',
    actions: [
      { label: 'Dashboard One', ariaLabel: 'Dashboard One', onClick: vi.fn() },
      { label: 'Dashboard Two', ariaLabel: 'Dashboard Two', onClick: vi.fn() }
    ]
  },
  {
    heading: 'Export',
    actions: [{ label: 'Export as JSON', ariaLabel: 'Export as JSON', onClick: vi.fn() }]
  }
]

const ARIA_LABEL = 'Action menu'

test('exposes the trigger button via its ariaLabel', () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS, ariaLabel: ARIA_LABEL } })
  expect(screen.getByRole('button', { name: ARIA_LABEL })).toBeInTheDocument()
})

test('dropdown is not visible initially', () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS, ariaLabel: ARIA_LABEL } })
  expect(screen.queryByText('Add to dashboard')).not.toBeInTheDocument()
})

test('dropdown is disabled if no entries are provided', () => {
  render(GraphBurgerMenu, { props: { groups: [], ariaLabel: ARIA_LABEL } })
  expect(screen.getByRole('button', { name: ARIA_LABEL })).toBeDisabled()
})

test('clicking the trigger shows the dropdown with group headings and actions', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS, ariaLabel: ARIA_LABEL } })
  await fireEvent.click(screen.getByRole('button', { name: ARIA_LABEL }))
  expect(screen.getByText('Add to dashboard')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Dashboard One' })).toBeInTheDocument()
  expect(screen.getByText('Export')).toBeInTheDocument()
})

test('clicking an action emits doAction with its onClick and closes the dropdown', async () => {
  const { emitted } = render(GraphBurgerMenu, { props: { groups: GROUPS, ariaLabel: ARIA_LABEL } })
  await fireEvent.click(screen.getByRole('button', { name: ARIA_LABEL }))
  await fireEvent.click(screen.getByRole('button', { name: 'Dashboard One' }))
  expect(emitted().doAction![0]).toEqual([GROUPS[0]!.actions[0]!.onClick])
  expect(screen.queryByText('Dashboard One')).not.toBeInTheDocument()
})

test('clicking outside the component closes the dropdown', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS, ariaLabel: ARIA_LABEL } })
  await fireEvent.click(screen.getByRole('button', { name: ARIA_LABEL }))
  expect(screen.getByText('Add to dashboard')).toBeInTheDocument()
  await fireEvent.click(document.body)
  expect(screen.queryByText('Add to dashboard')).not.toBeInTheDocument()
})

test('pressing escape key closes the dropdown', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS, ariaLabel: ARIA_LABEL } })
  await fireEvent.click(screen.getByRole('button', { name: ARIA_LABEL }))
  expect(screen.getByText('Add to dashboard')).toBeInTheDocument()
  await fireEvent.keyDown(document.body, { key: 'Escape', code: 'Escape' })
  expect(screen.queryByText('Add to dashboard')).not.toBeInTheDocument()
})

test('constrains the dropdown height to the remaining viewport space when scrollable', async () => {
  vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(500)
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    bottom: 100
  } as DOMRect)

  render(GraphBurgerMenu, { props: { groups: GROUPS, scrollable: true, ariaLabel: ARIA_LABEL } })
  await fireEvent.click(screen.getByRole('button', { name: ARIA_LABEL }))

  const dropdown = screen
    .getByText('Add to dashboard')
    .closest('.graphing-graph-burger-menu__dropdown')
  expect(dropdown).toHaveStyle({ maxHeight: '360px' })
})

test('does not constrain the dropdown height when scrollable is disabled', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS, scrollable: false, ariaLabel: ARIA_LABEL } })
  await fireEvent.click(screen.getByRole('button', { name: ARIA_LABEL }))

  const dropdown = screen
    .getByText('Add to dashboard')
    .closest('.graphing-graph-burger-menu__dropdown')
  expect((dropdown as HTMLElement).style.maxHeight).toBe('')
})
