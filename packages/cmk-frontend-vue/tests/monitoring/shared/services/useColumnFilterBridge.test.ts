/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnFiltersState } from '@tanstack/vue-table'
import { describe, expect, it } from 'vitest'

import type { ConditionNode, FilterField, FilterNode } from '@/monitoring/shared/api/types'
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
  {
    accessorKey: 'services_col',
    meta: { filter: { type: 'numeric', field: 'num_services' } }
  },
  {
    accessorKey: 'modes_col',
    meta: {
      filter: {
        type: 'boolean-group',
        groups: [
          { field: 'in_downtime', title: 'In downtime' },
          { field: 'acknowledged', title: 'Acknowledged' }
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
const servicesRange: FilterNode = {
  type: 'and',
  children: [
    { type: 'condition', field: 'num_services', op: 'gte', value: 3 },
    { type: 'condition', field: 'num_services', op: 'lte', value: 10 }
  ]
}
const inDowntime: ConditionNode = {
  type: 'condition',
  field: 'in_downtime',
  op: 'eq',
  value: true
}
const acknowledged: ConditionNode = {
  type: 'condition',
  field: 'acknowledged',
  op: 'eq',
  value: false
}
const modesBoth: FilterNode = { type: 'and', children: [inDowntime, acknowledged] }

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

    store.setColumnFilters(
      new Map<FilterField, FilterNode | undefined>([
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

    expect(store.getColumnFilter('name')).toStrictEqual(name)
    expect(store.getColumnFilter('alias')).toStrictEqual(alias)
    expect(store.getColumnFilter('state')).toBeUndefined()
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

    store.setColumnFilters(
      new Map<FilterField, FilterNode | undefined>([
        ['name', name],
        ['alias', alias],
        ['state', state]
      ])
    )
    const before = store.filterNode.value

    // Feed the derived table state straight back through the update handler.
    bridge.onColumnFiltersUpdate(bridge.tableColumnFilters.value)

    expect(store.getColumnFilter('name')).toStrictEqual(name)
    expect(store.getColumnFilter('alias')).toStrictEqual(alias)
    expect(store.getColumnFilter('state')).toStrictEqual(state)
    expect(store.activeFilterCount).toBe(3)
    // The set of top-level conditions is unchanged by the round trip.
    expect(store.filterNode.value).toStrictEqual(before)
  })

  it('round trips a numeric range (two conditions on one field) without dropping a bound', () => {
    const { store, bridge } = makeBridge()

    bridge.onColumnFiltersUpdate([{ id: 'services_col', value: servicesRange }])

    // Both bounds survive: the column value is recovered as the full and node.
    expect(store.getColumnFilter('num_services')).toStrictEqual(servicesRange)
    expect(bridge.tableColumnFilters.value).toStrictEqual([
      { id: 'services_col', value: servicesRange }
    ])
    // A range counts as a single active column filter, not two.
    expect(store.activeFilterCount).toBe(1)
  })

  it('keeps a numeric range intact alongside other column filters', () => {
    const { store, bridge } = makeBridge()

    bridge.onColumnFiltersUpdate([
      { id: 'name_col', value: name },
      { id: 'services_col', value: servicesRange }
    ])

    expect(store.getColumnFilter('name')).toStrictEqual(name)
    expect(store.getColumnFilter('num_services')).toStrictEqual(servicesRange)
    expect(store.activeFilterCount).toBe(2)
  })

  it('clears a condition when the column is dropped from the table state', () => {
    const { store, bridge } = makeBridge()

    store.setColumnFilters(
      new Map([
        ['name', name],
        ['alias', alias]
      ])
    )

    // Drop the alias filter: the next table state only carries name.
    bridge.onColumnFiltersUpdate([{ id: 'name_col', value: name }])

    expect(store.getColumnFilter('name')).toStrictEqual(name)
    expect(store.getColumnFilter('alias')).toBeUndefined()
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
    expect(store.getColumnFilter('name')).toStrictEqual(name)
    expect(bridge.tableColumnFilters.value).toStrictEqual([{ id: 'name_col', value: name }])
  })

  it('combines a boolean group filter across fields into one column value', () => {
    const { store, bridge } = makeBridge()

    store.setColumnFilters(
      new Map<FilterField, FilterNode | undefined>([
        ['in_downtime', inDowntime],
        ['acknowledged', acknowledged]
      ])
    )

    expect(bridge.tableColumnFilters.value).toContainEqual({ id: 'modes_col', value: modesBoth })
  })

  it('splits a boolean group filter node back into per-field store conditions', () => {
    const { store, bridge } = makeBridge()

    bridge.onColumnFiltersUpdate([{ id: 'modes_col', value: modesBoth }])

    expect(store.getColumnFilter('in_downtime')).toStrictEqual(inDowntime)
    expect(store.getColumnFilter('acknowledged')).toStrictEqual(acknowledged)
    expect(store.activeFilterCount).toBe(2)
  })

  it('round trips a single active boolean group as a lone condition', () => {
    const { store, bridge } = makeBridge()

    bridge.onColumnFiltersUpdate([{ id: 'modes_col', value: inDowntime }])

    expect(store.getColumnFilter('in_downtime')).toStrictEqual(inDowntime)
    expect(store.getColumnFilter('acknowledged')).toBeUndefined()
    expect(bridge.tableColumnFilters.value).toContainEqual({ id: 'modes_col', value: inDowntime })
  })

  it('keeps flags combined with OR as one node through the store', () => {
    const { store, bridge } = makeBridge()
    const modesEither: FilterNode = { type: 'or', children: [inDowntime, acknowledged] }

    bridge.onColumnFiltersUpdate([
      { id: 'state_col', value: state },
      { id: 'modes_col', value: modesEither }
    ])

    expect(store.filterNode.value).toStrictEqual({ type: 'and', children: [state, modesEither] })
    expect(bridge.tableColumnFilters.value).toContainEqual({ id: 'modes_col', value: modesEither })
    expect(store.activeFilterCount).toBe(3)
  })

  it('replaces flags combined with OR when the column changes', () => {
    const { store, bridge } = makeBridge()

    bridge.onColumnFiltersUpdate([
      { id: 'modes_col', value: { type: 'or', children: [inDowntime, acknowledged] } }
    ])
    bridge.onColumnFiltersUpdate([{ id: 'modes_col', value: inDowntime }])

    expect(store.filterNode.value).toStrictEqual(inDowntime)
  })

  it('clears every condition when the table state goes empty', () => {
    const { store, bridge } = makeBridge()

    store.setColumnFilters(new Map([['name', name]]))

    bridge.onColumnFiltersUpdate([])

    expect(store.filterNode.value).toBeUndefined()
    expect(store.activeFilterCount).toBe(0)
    expect(bridge.tableColumnFilters.value).toStrictEqual([])
  })
})
