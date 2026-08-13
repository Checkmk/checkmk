/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnFiltersState, VisibilityState } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, defineComponent, h, provide, ref } from 'vue'

import ColumnPicker from '@/monitoring/shared/components/ColumnPicker.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import type { ToggleableColumn } from '@/monitoring/shared/tableState/schema'

function t(value: string): TranslatedString {
  return value as TranslatedString
}

const TOGGLEABLE: ToggleableColumn[] = [
  { id: 'address', label: t('IP address') },
  { id: 'alias', label: t('Alias') }
]

const DEFAULT_VISIBILITY: VisibilityState = { alias: false }

function mountPicker(
  visibility: VisibilityState = { ...DEFAULT_VISIBILITY },
  columnFilters: ColumnFiltersState = []
) {
  const columnVisibility = ref<VisibilityState>({ ...visibility })
  const updateColumnVisibility = vi.fn((next: VisibilityState) => {
    columnVisibility.value = next
  })
  const resetColumnVisibility = vi.fn(() => {
    columnVisibility.value = withFilteredColumnsShown({ ...DEFAULT_VISIBILITY })
  })
  function withFilteredColumnsShown(visibility: VisibilityState): VisibilityState {
    const filtered = new Set(columnFilters.map((filter) => filter.id))
    const guarded = { ...visibility }
    for (const { id } of TOGGLEABLE) {
      if (filtered.has(id) && columnVisibility.value[id] !== false) {
        guarded[id] = true
      }
    }
    return guarded
  }
  const mockService = {
    toggleableColumns: TOGGLEABLE,
    columnVisibility,
    defaultColumnVisibility: { ...DEFAULT_VISIBILITY },
    updateColumnVisibility: vi.fn((next: VisibilityState) =>
      updateColumnVisibility(withFilteredColumnsShown(next))
    ),
    resetColumnVisibility,
    withFilteredColumnsShown,
    tableColumnFilters: computed(() => columnFilters),
    beginAutoPause: vi.fn(),
    endAutoPause: vi.fn()
  }

  const utils = render(
    defineComponent({
      setup() {
        provide(MONITORING_SERVICE, mockService as unknown as MonitoringService<unknown>)
        return () => h(ColumnPicker)
      }
    })
  )
  return { ...utils, updateColumnVisibility, resetColumnVisibility, columnVisibility }
}

async function openPicker() {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Show or hide columns' }))
  return user
}

test('the popover is closed until the trigger is clicked', async () => {
  mountPicker()

  const trigger = screen.getByRole('button', { name: 'Show or hide columns' })
  expect(trigger).toHaveAttribute('aria-expanded', 'false')
  expect(screen.queryByRole('button', { name: 'Alias' })).not.toBeInTheDocument()

  await openPicker()

  expect(trigger).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByRole('button', { name: 'Alias' })).toBeInTheDocument()
})

test('renders one eye toggle per column in column order, with a search field', async () => {
  mountPicker()

  await openPicker()

  expect(screen.getByRole('textbox', { name: 'Search' })).toBeInTheDocument()
  const address = screen.getByRole('button', { name: 'IP address' })
  const alias = screen.getByRole('button', { name: 'Alias' })
  expect(address.compareDocumentPosition(alias) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})

test('the eye toggle reflects the committed visibility via aria-pressed', async () => {
  mountPicker({ alias: false })

  await openPicker()

  expect(screen.getByRole('button', { name: 'IP address', pressed: true })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Alias', pressed: false })).toBeInTheDocument()
})

test('a toggle stages in the popover but does not touch the service before Apply', async () => {
  const { updateColumnVisibility, columnVisibility } = mountPicker({ alias: false })

  const user = await openPicker()
  await user.click(screen.getByRole('button', { name: 'Alias' }))

  expect(screen.getByRole('button', { name: 'Alias', pressed: true })).toBeInTheDocument()
  expect(updateColumnVisibility).not.toHaveBeenCalled()
  expect(columnVisibility.value).toEqual({ alias: false })
})

test('Apply commits the staged visibility to the service', async () => {
  const { updateColumnVisibility } = mountPicker({ alias: false })

  const user = await openPicker()
  await user.click(screen.getByRole('button', { name: 'Alias' }))
  await user.click(screen.getByRole('button', { name: 'IP address' }))
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(updateColumnVisibility).toHaveBeenCalledTimes(1)
  expect(updateColumnVisibility).toHaveBeenCalledWith({ alias: true, address: false })
})

test('Cancel discards the staged changes', async () => {
  const { updateColumnVisibility, columnVisibility } = mountPicker({ alias: false })

  const user = await openPicker()
  await user.click(screen.getByRole('button', { name: 'Alias' }))
  await user.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(updateColumnVisibility).not.toHaveBeenCalled()
  expect(columnVisibility.value).toEqual({ alias: false })
})

test('closing via click-outside discards the staged changes', async () => {
  const { updateColumnVisibility, columnVisibility } = mountPicker({ alias: false })

  const user = await openPicker()
  await user.click(screen.getByRole('button', { name: 'Alias' }))
  await user.click(document.body)

  expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument()
  expect(updateColumnVisibility).not.toHaveBeenCalled()
  expect(columnVisibility.value).toEqual({ alias: false })
})

test('the search field filters the offered columns', async () => {
  mountPicker()

  const user = await openPicker()
  await user.type(screen.getByRole('textbox', { name: 'Search' }), 'ip')

  expect(screen.getByRole('button', { name: 'IP address' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Alias' })).not.toBeInTheDocument()
})

test('an empty search result shows the empty state', async () => {
  mountPicker()

  const user = await openPicker()
  await user.type(screen.getByRole('textbox', { name: 'Search' }), 'zzz')

  expect(screen.getByText('No matching columns')).toBeInTheDocument()
})

test('"Back to default" stages the default set and commits it on Apply', async () => {
  const { resetColumnVisibility } = mountPicker({ alias: true, address: false })

  const user = await openPicker()
  await user.click(screen.getByRole('button', { name: 'Back to default' }))

  expect(screen.getByRole('button', { name: 'IP address', pressed: true })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Alias', pressed: false })).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Apply' }))
  expect(resetColumnVisibility).toHaveBeenCalledTimes(1)
})

test('a column filtering the listing cannot be hidden', async () => {
  const { updateColumnVisibility } = mountPicker({ alias: false }, [
    { id: 'address', value: { type: 'contains', field: 'address', value: '10.' } }
  ])

  const user = await openPicker()
  const address = screen.getByRole('button', { name: 'IP address' })

  expect(address).toHaveAttribute('aria-disabled', 'true')

  await user.click(address)
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(address).toHaveAttribute('aria-pressed', 'true')
  expect(updateColumnVisibility).not.toHaveBeenCalled()
})

test('a filtered column keeps its hint reachable, not on a disabled button', async () => {
  mountPicker({ alias: false }, [
    { id: 'address', value: { type: 'contains', field: 'address', value: '10.' } }
  ])

  await openPicker()
  const address = screen.getByRole('button', { name: 'IP address' })

  // A native `disabled` button gets no hover in Chromium, so the title would never show.
  expect(address).toBeEnabled()
  expect(address).toHaveAttribute('title', 'Clear the filter on IP address before hiding it')
})

test('"Back to default" cannot hide a filtered column either', async () => {
  const { columnVisibility } = mountPicker({ alias: true, address: true }, [
    { id: 'alias', value: { type: 'contains', field: 'alias', value: 'web' } }
  ])

  const user = await openPicker()
  await user.click(screen.getByRole('button', { name: 'Back to default' }))

  // `alias` is hidden by default, so the unguarded reset used to drop it while its filter stayed on.
  expect(screen.getByRole('button', { name: 'Alias', pressed: true })).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(columnVisibility.value['alias']).not.toBe(false)
})

test('a column without a filter stays hideable while another one is filtered', async () => {
  const { updateColumnVisibility } = mountPicker({ alias: true }, [
    { id: 'address', value: { type: 'contains', field: 'address', value: '10.' } }
  ])

  const user = await openPicker()
  const alias = screen.getByRole('button', { name: 'Alias' })

  expect(alias).toBeEnabled()

  await user.click(alias)
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  // `address` comes back explicitly shown: it is filtered, so the service pins it.
  expect(updateColumnVisibility).toHaveBeenCalledWith({ alias: false, address: true })
})

test('a hidden column can still be shown while its filter is active', async () => {
  const { updateColumnVisibility } = mountPicker({ alias: false }, [
    { id: 'alias', value: { type: 'contains', field: 'alias', value: 'web' } }
  ])

  const user = await openPicker()
  const alias = screen.getByRole('button', { name: 'Alias' })

  expect(alias).toBeEnabled()

  await user.click(alias)
  await user.click(screen.getByRole('button', { name: 'Apply' }))

  expect(updateColumnVisibility).toHaveBeenCalledWith({ alias: true })
})
