/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnFiltersState } from '@tanstack/vue-table'
import { describe, expect, it } from 'vitest'

import type { ConditionNode, FilterField } from '@/monitoring/shared/api/types'
import '@/monitoring/shared/components/MonitoringTableContext'
import { FilterStore } from '@/monitoring/shared/services/FilterStore'
import { useColumnFilterBridge } from '@/monitoring/shared/services/useColumnFilterBridge'

interface Host {
  name: string
  alias: string
  state: string
  unfilterable: string
}

// `accessorKey` (the table column id) intentionally differs from the filter
// `field` so the round trip exercises the id <-> field mapping rather than an
// identity pass-through.
const columns: ColumnDef<Host>[] = [
  {
    accessorKey: 'name_col',
    meta: { filter: { type: 'string-input', field: 'name' } }
  },
  {
    accessorKey: 'alias_col',
    meta: { filter: { type: 'string-input', field: 'alias' } }
  },
  {
    accessorKey: 'state_col',
    meta: {
      filter: {
        type: 'checkbox-list',
        field: 'state',
        options: [
          { value: 'UP', title: 'Up' },
          { value: 'DOWN', title: 'Down' }
        ]
      }
    }
  },
  // No filter meta -> the bridge must ignore this column in both directions.
  { accessorKey: 'unfilterable' }
]

const name: ConditionNode = { type: 'condition', field: 'name', op: 'contains', value: 'heute' }
const alias: ConditionNode = { type: 'condition', field: 'alias', op: 'contains', value: 'db' }
const state: ConditionNode = { type: 'condition', field: 'state', op: 'one_of', value: ['DOWN'] }

function makeBridge(): {
  store: FilterStore
  bridge: ReturnType<typeof useColumnFilterBridge<Host>>
} {
  const store = new FilterStore([])
  const bridge = useColumnFilterBridge(columns, store)
  return { store, bridge }
}

describe('useColumnFilterBridge round trip', () => {
  it('starts with no column filters when the store is empty', () => {
    const { bridge } = makeBridge()

    expect(bridge.tableColumnFilters.value).toStrictEqual([])
  })

  it('derives table column filters from the store, keyed by accessorKey', () => {
    const { store, bridge } = makeBridge()

    store.setColumnConditions(
      new Map<FilterField, ConditionNode | undefined>([
        ['name', name],
        ['state', state]
      ])
    )

    expect(bridge.tableColumnFilters.value).toStrictEqual([
      { id: 'name_col', value: name },
      { id: 'state_col', value: state }
    ])
  })

  it('writes table column filter updates back into the store, keyed by field', () => {
    const { store, bridge } = makeBridge()

    bridge.onColumnFiltersUpdate([
      { id: 'name_col', value: name },
      { id: 'alias_col', value: alias }
    ])

    expect(store.getColumnCondition('name')).toStrictEqual(name)
    expect(store.getColumnCondition('alias')).toStrictEqual(alias)
    expect(store.getColumnCondition('state')).toBeUndefined()
  })

  it('preserves the column filter state across a table -> store -> table round trip', () => {
    const { bridge } = makeBridge()

    const initial: ColumnFiltersState = [
      { id: 'name_col', value: name },
      { id: 'alias_col', value: alias },
      { id: 'state_col', value: state }
    ]

    bridge.onColumnFiltersUpdate(initial)

    expect(bridge.tableColumnFilters.value).toStrictEqual(initial)
  })

  it('preserves the store conditions across a store -> table -> store round trip', () => {
    const { store, bridge } = makeBridge()

    store.setColumnConditions(
      new Map<FilterField, ConditionNode | undefined>([
        ['name', name],
        ['alias', alias],
        ['state', state]
      ])
    )
    const before = store.filterNode.value

    // Feed the derived table state straight back through the update handler.
    bridge.onColumnFiltersUpdate(bridge.tableColumnFilters.value)

    expect(store.getColumnCondition('name')).toStrictEqual(name)
    expect(store.getColumnCondition('alias')).toStrictEqual(alias)
    expect(store.getColumnCondition('state')).toStrictEqual(state)
    expect(store.activeFilterCount).toBe(3)
    // The set of top-level conditions is unchanged by the round trip.
    expect(store.filterNode.value).toStrictEqual(before)
  })

  it('clears a condition when the column is dropped from the table state', () => {
    const { store, bridge } = makeBridge()

    store.setColumnConditions(
      new Map([
        ['name', name],
        ['alias', alias]
      ])
    )

    // Drop the alias filter: the next table state only carries name.
    bridge.onColumnFiltersUpdate([{ id: 'name_col', value: name }])

    expect(store.getColumnCondition('name')).toStrictEqual(name)
    expect(store.getColumnCondition('alias')).toBeUndefined()
    expect(bridge.tableColumnFilters.value).toStrictEqual([{ id: 'name_col', value: name }])
  })

  it('ignores table entries for columns without a filter field', () => {
    const { store, bridge } = makeBridge()

    bridge.onColumnFiltersUpdate([
      { id: 'name_col', value: name },
      {
        id: 'unfilterable',
        value: { type: 'condition', field: 'name', op: 'contains', value: 'x' }
      }
    ])

    expect(store.activeFilterCount).toBe(1)
    expect(store.getColumnCondition('name')).toStrictEqual(name)
    expect(bridge.tableColumnFilters.value).toStrictEqual([{ id: 'name_col', value: name }])
  })

  it('clears every condition when the table state goes empty', () => {
    const { store, bridge } = makeBridge()

    store.setColumnConditions(new Map([['name', name]]))

    bridge.onColumnFiltersUpdate([])

    expect(store.filterNode.value).toBeUndefined()
    expect(store.activeFilterCount).toBe(0)
    expect(bridge.tableColumnFilters.value).toStrictEqual([])
  })
})
