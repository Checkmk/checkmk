/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as intl from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'

import GraphHeader from '@/graphing/components/header/GraphHeader.vue'
import type { BurgerMenuGroup } from '@/graphing/types'

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, getLocalTimeZone: () => 'UTC' }
})

const JUNE_15_NOON_UTC = 1781524800
const JUNE_14_NOON_UTC = JUNE_15_NOON_UTC - 86400

test('shows the graph title when showTitle is set', () => {
  render(GraphHeader, { props: { showTitle: true, title: 'CPU utilization' } })

  expect(screen.getByText('CPU utilization')).toBeInTheDocument()
})

test('omits the graph title when showTitle is not set', () => {
  render(GraphHeader, { props: { title: 'CPU utilization' } })

  expect(screen.queryByText('CPU utilization')).not.toBeInTheDocument()
})

const AGGREGATED_TIME_RANGE = { start: JUNE_15_NOON_UTC, end: JUNE_15_NOON_UTC + 3600, step: 300 }
const RAW_TIME_RANGE = { start: JUNE_15_NOON_UTC, end: JUNE_15_NOON_UTC + 3600, step: 60 }

test('the consolidation dropdown shows the selected function', async () => {
  render(GraphHeader, {
    props: { showConsolidation: true, consolidationFn: 'max', timeRange: AGGREGATED_TIME_RANGE }
  })

  await waitFor(() =>
    expect(screen.getByRole('combobox', { name: 'Graph values' })).toHaveTextContent('Max')
  )
})

test('selecting a consolidation function shows the new selection and emits update:consolidationFn', async () => {
  const user = userEvent.setup()
  const { emitted } = render(GraphHeader, {
    props: { showConsolidation: true, consolidationFn: 'max', timeRange: AGGREGATED_TIME_RANGE }
  })
  const dropdown = screen.getByRole('combobox', { name: 'Graph values' })

  await user.click(dropdown)
  await user.click(await screen.findByRole('option', { name: 'Min' }))
  expect(dropdown).toHaveTextContent('Min')
  expect(emitted('update:consolidationFn')?.at(-1)).toEqual(['min'])

  await user.click(dropdown)
  await user.click(await screen.findByRole('option', { name: 'Average' }))
  expect(dropdown).toHaveTextContent('Average')
  expect(emitted('update:consolidationFn')?.at(-1)).toEqual(['avg'])
})

test('describes a same-day range with a single date and its resolution', () => {
  render(GraphHeader, {
    props: {
      showTimestamp: true,
      timeRange: { start: JUNE_15_NOON_UTC, end: JUNE_15_NOON_UTC + 3600, step: 300 }
    }
  })

  expect(screen.getByText('for 2026-06-15,')).toBeInTheDocument()
  expect(screen.getByText('resolution: 5 min')).toBeInTheDocument()
})

test('describes a cross-day range as start — end', () => {
  render(GraphHeader, {
    props: {
      showTimestamp: true,
      timeRange: { start: JUNE_14_NOON_UTC, end: JUNE_15_NOON_UTC, step: 21600 }
    }
  })

  expect(screen.getByText('for 2026-06-14 — 2026-06-15,')).toBeInTheDocument()
  expect(screen.getByText('resolution: 6 h')).toBeInTheDocument()
})

test('omits the range note while no time range is known', () => {
  render(GraphHeader, { props: { showTimestamp: true } })

  expect(screen.queryByText(/resolution:/)).not.toBeInTheDocument()
})

test('offers a zoom selector with an X and a Y mode', () => {
  render(GraphHeader, {})

  expect(screen.getByText('X-zoom')).toBeInTheDocument()
  expect(screen.getByText('Y-zoom')).toBeInTheDocument()
})

test('the zoom selector reflects peak zoom as the checked state', () => {
  render(GraphHeader, { props: { zoomMode: 'value' } })

  expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true')
})

test('switching the zoom mode emits update:zoomMode', async () => {
  const { emitted } = render(GraphHeader, { props: { zoomMode: 'time' } })

  await fireEvent.click(screen.getByRole('switch'))

  expect(emitted()['update:zoomMode']).toEqual([['value']])
})

test('omits the consolidation dropdown unless showConsolidation is set', () => {
  render(GraphHeader, { props: { timeRange: AGGREGATED_TIME_RANGE } })

  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
})

test('shows the consolidation dropdown when showConsolidation is set and the data is aggregated', () => {
  render(GraphHeader, { props: { showConsolidation: true, timeRange: AGGREGATED_TIME_RANGE } })

  expect(screen.getByRole('combobox', { name: 'Graph values' })).toBeInTheDocument()
})

test('hides the consolidation dropdown while the time range is unknown', () => {
  render(GraphHeader, { props: { showConsolidation: true } })

  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
})

test('hides the consolidation dropdown once the data is at raw, unaggregated resolution', () => {
  render(GraphHeader, { props: { showConsolidation: true, timeRange: RAW_TIME_RANGE } })

  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
})

test('hides the zoom selector when showControls is false', () => {
  render(GraphHeader, { props: { showControls: false } })

  expect(screen.queryByRole('switch')).not.toBeInTheDocument()
})

test('shows the burger action menu when showBurgerMenu is set - BP-C01', async () => {
  const groups: BurgerMenuGroup[] = [
    {
      heading: 'Export',
      actions: [{ label: 'Export as JSON', ariaLabel: 'Export as JSON', onClick: vi.fn() }]
    }
  ]
  render(GraphHeader, {
    props: { showControls: false, showBurgerMenu: true, burgerMenuGroups: groups }
  })

  await fireEvent.click(screen.getByRole('button'))

  expect(screen.getByText('Export')).toBeInTheDocument()
})

test('exposes the controls as an accessible group', () => {
  render(GraphHeader, { props: { showBurgerMenu: true, burgerMenuGroups: [] } })

  expect(
    screen.getByRole('group', { name: 'Graph zoom controls and action menu' })
  ).toBeInTheDocument()
})

test('draws the burger menu inside the header trailing action group', () => {
  const groups: BurgerMenuGroup[] = [
    {
      heading: 'Export',
      actions: [{ label: 'Export as JSON', ariaLabel: 'Export as JSON', onClick: vi.fn() }]
    }
  ]
  render(GraphHeader, {
    props: {
      showTitle: true,
      title: 'CPU utilization',
      showConsolidation: true,
      timeRange: AGGREGATED_TIME_RANGE,
      showBurgerMenu: true,
      burgerMenuGroups: groups
    }
  })

  const [valuesAndTimeGroup, zoomAndMenuGroup] = screen.getAllByRole('group')

  expect(valuesAndTimeGroup).toHaveAccessibleName('Graph values and time information')
  expect(zoomAndMenuGroup).toHaveAccessibleName('Graph zoom controls and action menu')
  expect(within(zoomAndMenuGroup!).getByRole('button')).toBeInTheDocument()
})
