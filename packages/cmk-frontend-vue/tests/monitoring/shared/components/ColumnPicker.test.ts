/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { VisibilityState } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { defineComponent, h, provide, ref } from 'vue'

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

function mountPicker(visibility: VisibilityState = { ...DEFAULT_VISIBILITY }) {
  const columnVisibility = ref<VisibilityState>({ ...visibility })
  const updateColumnVisibility = vi.fn((next: VisibilityState) => {
    columnVisibility.value = next
  })
  const resetColumnVisibility = vi.fn(() => {
    columnVisibility.value = { ...DEFAULT_VISIBILITY }
  })
  const mockService = {
    toggleableColumns: TOGGLEABLE,
    columnVisibility,
    defaultColumnVisibility: { ...DEFAULT_VISIBILITY },
    updateColumnVisibility,
    resetColumnVisibility,
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
