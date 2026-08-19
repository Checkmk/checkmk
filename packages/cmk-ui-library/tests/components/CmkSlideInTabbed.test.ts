/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkSlideInTabbed from 'cmk-ui-library/components/CmkSlideInTabbed/CmkSlideInTabbed.vue'
import type { SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed/types'
import { defineComponent, h, markRaw } from 'vue'

const tabBody = markRaw(
  defineComponent({
    props: { data: { type: String, default: '' } },
    setup: (props) => () => h('div', { 'data-testid': 'tab-body' }, props.data)
  })
)

const header = { title: 'Host', closeButton: true }

test('loads and renders the active tab content', async () => {
  const load = vi.fn().mockResolvedValue('resolved content')
  const tabs: SlideInTab[] = [{ id: 'a', title: 'A', component: tabBody, load }]

  render(CmkSlideInTabbed, { props: { open: true, tabs, header } })

  await screen.findByText('resolved content')
  expect(load).toHaveBeenCalledTimes(1)
})

test('shows an error with a retry that reloads the tab', async () => {
  const load = vi
    .fn()
    .mockRejectedValueOnce(new Error('boom'))
    .mockResolvedValueOnce('recovered content')
  const tabs: SlideInTab[] = [{ id: 'a', title: 'A', component: tabBody, load }]

  render(CmkSlideInTabbed, { props: { open: true, tabs, header } })

  await screen.findByText('Could not load this content.')
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }))

  await screen.findByText('recovered content')
  expect(load).toHaveBeenCalledTimes(2)
})

test('renders the actions slot alongside the tabs by default', async () => {
  const tabs: SlideInTab[] = [{ id: 'a', title: 'A', component: tabBody }]

  render(CmkSlideInTabbed, {
    props: { open: true, tabs, header },
    slots: {
      actions: () => h('div', { 'data-testid': 'actions' }, 'action buttons'),
      override: () => h('div', { 'data-testid': 'override' }, 'override view')
    }
  })

  await screen.findByTestId('actions')
  expect(screen.getByRole('tab', { name: 'A' })).toBeInTheDocument()
  expect(screen.queryByTestId('override')).not.toBeInTheDocument()
})

test('replaces the tabs and actions with the override slot when active', async () => {
  const tabs: SlideInTab[] = [{ id: 'a', title: 'A', component: tabBody }]

  render(CmkSlideInTabbed, {
    props: { open: true, tabs, header, overrideActive: true },
    slots: {
      actions: () => h('div', { 'data-testid': 'actions' }, 'action buttons'),
      override: () => h('div', { 'data-testid': 'override' }, 'override view')
    }
  })

  await screen.findByTestId('override')
  expect(screen.queryByTestId('actions')).not.toBeInTheDocument()
  expect(screen.queryByRole('tab', { name: 'A' })).not.toBeInTheDocument()
})

test('caches loaded tabs and re-fetches only on reopen', async () => {
  const loadA = vi.fn().mockResolvedValue('a-data')
  const loadB = vi.fn().mockResolvedValue('b-data')
  const tabs: SlideInTab[] = [
    { id: 'a', title: 'A', component: tabBody, load: loadA },
    { id: 'b', title: 'B', component: tabBody, load: loadB }
  ]

  const { rerender } = render(CmkSlideInTabbed, { props: { open: true, tabs, header } })

  await screen.findByText('a-data')
  await userEvent.click(screen.getByRole('tab', { name: 'B' }))
  await screen.findByText('b-data')
  await userEvent.click(screen.getByRole('tab', { name: 'A' }))
  await screen.findByText('a-data')
  expect(loadA).toHaveBeenCalledTimes(1)

  await rerender({ open: false, tabs, header })
  await rerender({ open: true, tabs, header })

  await screen.findByText('a-data')
  expect(loadA).toHaveBeenCalledTimes(2)
})

test('reports the tab the user picked, so a page can outlive the panel with it', async () => {
  const tabs: SlideInTab[] = [
    { id: 'a', title: 'A', component: tabBody },
    { id: 'b', title: 'B', component: tabBody }
  ]

  const { emitted } = render(CmkSlideInTabbed, { props: { open: true, tabs, header } })

  await userEvent.click(await screen.findByRole('tab', { name: 'B' }))

  // Only what the user picked: opening on the default tab is not news.
  expect(emitted()['update:activeTabId']).toEqual([['b']])
})

test('opens on the bound tab rather than the first one', async () => {
  const loadA = vi.fn().mockResolvedValue('a-data')
  const loadB = vi.fn().mockResolvedValue('b-data')
  const tabs: SlideInTab[] = [
    { id: 'a', title: 'A', component: tabBody, load: loadA },
    { id: 'b', title: 'B', component: tabBody, load: loadB }
  ]

  render(CmkSlideInTabbed, { props: { open: true, tabs, header, activeTabId: 'b' } })

  await screen.findByText('b-data')
  expect(loadA).not.toHaveBeenCalled()
})

test('falls back to the first tab when the bound tab is dropped', async () => {
  const tabs: SlideInTab[] = [
    { id: 'a', title: 'A', component: tabBody, load: () => Promise.resolve('a-data') },
    { id: 'b', title: 'B', component: tabBody, load: () => Promise.resolve('b-data') }
  ]

  const { rerender } = render(CmkSlideInTabbed, {
    props: { open: true, tabs, header, activeTabId: 'b' }
  })

  await screen.findByText('b-data')
  await rerender({ open: true, tabs, header, activeTabId: undefined })

  await screen.findByText('a-data')
  expect(screen.getByRole('tab', { name: 'A' })).toHaveAttribute('aria-selected', 'true')
})

test('falls back to the named default tab when the bound tab is dropped', async () => {
  const tabs: SlideInTab[] = [
    { id: 'a', title: 'A', component: tabBody, load: () => Promise.resolve('a-data') },
    { id: 'b', title: 'B', component: tabBody, load: () => Promise.resolve('b-data') }
  ]

  const { rerender } = render(CmkSlideInTabbed, {
    props: { open: true, tabs, header, defaultTabId: 'b', activeTabId: 'a' }
  })

  await screen.findByText('a-data')
  await rerender({ open: true, tabs, header, defaultTabId: 'b', activeTabId: undefined })

  await screen.findByText('b-data')
  expect(screen.getByRole('tab', { name: 'B' })).toHaveAttribute('aria-selected', 'true')
})

test('follows the bound tab when it changes from outside', async () => {
  const tabs: SlideInTab[] = [
    { id: 'a', title: 'A', component: tabBody, load: () => Promise.resolve('a-data') },
    { id: 'b', title: 'B', component: tabBody, load: () => Promise.resolve('b-data') }
  ]

  const { rerender } = render(CmkSlideInTabbed, {
    props: { open: true, tabs, header, activeTabId: 'a' }
  })

  await screen.findByText('a-data')
  await rerender({ open: true, tabs, header, activeTabId: 'b' })

  await screen.findByText('b-data')
})
