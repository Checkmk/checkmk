/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { vi } from 'vitest'
import { nextTick } from 'vue'

import ItemListSection from '@/graphing/designer/calculation/components/ItemListSection.vue'
import type { GraphItem, ItemId } from '@/graphing/designer/types'

import { formulaItem, rrdMetricItem } from '../../fixtures'

type SectionProps = InstanceType<typeof ItemListSection>['$props']

function renderSection(props: Partial<SectionProps> = {}) {
  return render(ItemListSection, {
    props: {
      heading: untranslated('Calculations'),
      emptyText: untranslated('No calculations yet.'),
      items: [rrdMetricItem('A'), formulaItem('D')],
      actionLabel: (id: ItemId) => untranslated(`Insert ${id}`),
      ...props
    }
  })
}

test('shows the empty text when there are no items', () => {
  renderSection({ items: [] })
  expect(screen.getByText('No calculations yet.')).toBeInTheDocument()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

test('renders the heading and one described row per item', () => {
  renderSection()
  expect(screen.getByRole('heading', { name: 'Calculations' })).toBeInTheDocument()
  expect(screen.getByText('my-host > CPU utilization > util')).toBeInTheDocument()
  expect(screen.getByText('= A')).toBeInTheDocument()
})

test('clicking a badge emits insertId with the item id', async () => {
  const { emitted } = renderSection()
  await fireEvent.click(screen.getByRole('button', { name: 'Insert A' }))
  expect(emitted('insertId')).toEqual([['A']])
})

test('itemBlockReason explains exactly the matching badges', () => {
  renderSection({
    itemBlockReason: (item: GraphItem) =>
      item.id === 'A' ? untranslated('Aggregate this query first') : null
  })
  const blocked = screen.getByRole('button', { name: 'Insert A' })
  expect(blocked).toHaveAttribute('aria-disabled', 'true')
  expect(blocked).toHaveAttribute('title', 'Aggregate this query first')
  expect(screen.getByRole('button', { name: 'Insert D' })).toHaveAttribute('aria-disabled', 'false')
})

test('edit and delete actions render only with showActions and emit the item id', async () => {
  const { emitted } = renderSection({ showActions: true })
  await fireEvent.click(screen.getByRole('button', { name: 'Edit A' }))
  await fireEvent.click(screen.getByRole('button', { name: 'Delete D' }))
  expect(emitted('edit')).toEqual([['A']])
  expect(emitted('delete')).toEqual([['D']])
})

test('actions are hidden by default', () => {
  renderSection()
  expect(screen.queryByRole('button', { name: 'Edit A' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Delete A' })).not.toBeInTheDocument()
})

test('shows the alert on the matching row and emits dismissAlert when it closes', async () => {
  vi.useFakeTimers()
  try {
    const { emitted } = renderSection({
      alert: { id: 'D', text: untranslated('Calculation added'), nonce: 1 }
    })
    const row = screen.getByText('Calculation added').closest('li')
    expect(row).toContainElement(screen.getByRole('button', { name: 'Insert D' }))
    vi.runAllTimers() // the alert auto-dismisses
    await nextTick()
    expect(emitted('dismissAlert')).toHaveLength(1)
  } finally {
    vi.useRealTimers()
  }
})
