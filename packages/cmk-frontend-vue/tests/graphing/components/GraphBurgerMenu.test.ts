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
      { label: 'Dashboard One', onClick: vi.fn() },
      { label: 'Dashboard Two', onClick: vi.fn() }
    ]
  },
  {
    heading: 'Export',
    actions: [{ label: 'Export as JSON', onClick: vi.fn() }]
  }
]

test('renders a trigger button', () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS } })
  expect(screen.getByRole('button')).toBeInTheDocument()
})

test('dropdown is not visible initially', () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS } })
  expect(screen.queryByText('Add to dashboard')).not.toBeInTheDocument()
})

test('clicking the trigger shows the dropdown with group headings and actions', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS } })
  await fireEvent.click(screen.getByRole('button'))
  expect(screen.getByText('Add to dashboard')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Dashboard One' })).toBeInTheDocument()
  expect(screen.getByText('Export')).toBeInTheDocument()
})

test('clicking an action calls its onClick and closes the dropdown', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS } })
  await fireEvent.click(screen.getByRole('button'))
  await fireEvent.click(screen.getByRole('button', { name: 'Dashboard One' }))
  expect(GROUPS[0]!.actions[0]!.onClick).toHaveBeenCalledOnce()
  expect(screen.queryByText('Dashboard One')).not.toBeInTheDocument()
})

test('clicking outside the component closes the dropdown', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS } })
  await fireEvent.click(screen.getByRole('button'))
  expect(screen.getByText('Add to dashboard')).toBeInTheDocument()
  await fireEvent.click(document.body)
  expect(screen.queryByText('Add to dashboard')).not.toBeInTheDocument()
})

test('renders a visual separator between multiple groups', async () => {
  render(GraphBurgerMenu, { props: { groups: GROUPS } })
  await fireEvent.click(screen.getByRole('button'))
  expect(screen.getByRole('separator')).toBeInTheDocument()
})
