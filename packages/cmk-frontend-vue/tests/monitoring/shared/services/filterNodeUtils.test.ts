/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { ConditionNode, FilterNode } from '@/monitoring/shared/api/types'
import { getTopLevelConditions, setCondition } from '@/monitoring/shared/services/filterNodeUtils'

const name: ConditionNode = { type: 'condition', field: 'name', op: 'contains', value: 'heute' }
const alias: ConditionNode = { type: 'condition', field: 'alias', op: 'contains', value: 'db' }
const acknowledged: ConditionNode = {
  type: 'condition',
  field: 'acknowledged',
  op: 'eq',
  value: true
}
const state: ConditionNode = { type: 'condition', field: 'state', op: 'one_of', value: ['DOWN'] }

describe('setCondition', () => {
  it('returns the bare condition when added to an empty filter', () => {
    expect(setCondition(undefined, 'name', name)).toStrictEqual(name)
  })

  it('combines two different fields into an and node', () => {
    const result = setCondition(name, 'acknowledged', acknowledged)

    expect(result).toStrictEqual({ type: 'and', children: [name, acknowledged] })
  })

  it('replaces the existing condition for the same field', () => {
    const updated: ConditionNode = { type: 'condition', field: 'name', op: 'matches', value: 'db' }

    expect(setCondition(name, 'name', updated)).toStrictEqual(updated)
  })

  it('replaces a field within an and node without touching the others', () => {
    const node: FilterNode = { type: 'and', children: [name, acknowledged] }
    const updated: ConditionNode = { type: 'condition', field: 'name', op: 'matches', value: 'db' }

    // The replaced field is removed and re-appended, so it moves to the end.
    expect(setCondition(node, 'name', updated)).toStrictEqual({
      type: 'and',
      children: [acknowledged, updated]
    })
  })

  it('adds a new field to an existing and node', () => {
    const node: FilterNode = { type: 'and', children: [name, acknowledged] }

    expect(setCondition(node, 'state', state)).toStrictEqual({
      type: 'and',
      children: [name, acknowledged, state]
    })
  })

  it('returns undefined when removing the only condition', () => {
    expect(setCondition(name, 'name', undefined)).toBeUndefined()
  })

  it('unwraps the and node when removal leaves a single condition', () => {
    const node: FilterNode = { type: 'and', children: [name, acknowledged] }

    expect(setCondition(node, 'name', undefined)).toStrictEqual(acknowledged)
  })

  it('keeps the and node when removal leaves multiple conditions', () => {
    const node: FilterNode = { type: 'and', children: [name, alias, acknowledged] }

    expect(setCondition(node, 'name', undefined)).toStrictEqual({
      type: 'and',
      children: [alias, acknowledged]
    })
  })

  it('is a no-op when removing a field that is not present', () => {
    const node: FilterNode = { type: 'and', children: [name, acknowledged] }

    expect(setCondition(node, 'state', undefined)).toStrictEqual(node)
  })

  it('does not mutate the input node', () => {
    const node: FilterNode = { type: 'and', children: [name, acknowledged] }
    const snapshot = structuredClone(node)

    setCondition(node, 'state', state)

    expect(node).toStrictEqual(snapshot)
  })
})

describe('getTopLevelConditions', () => {
  it('returns the single condition for a bare condition node', () => {
    expect(getTopLevelConditions(name)).toStrictEqual([name])
  })

  it('returns every condition child of an and node', () => {
    const node: FilterNode = { type: 'and', children: [name, acknowledged, state] }

    expect(getTopLevelConditions(node)).toStrictEqual([name, acknowledged, state])
  })

  it('ignores non-condition children of an and node', () => {
    const nested: FilterNode = { type: 'or', children: [name, alias] }
    const node: FilterNode = { type: 'and', children: [acknowledged, nested] }

    expect(getTopLevelConditions(node)).toStrictEqual([acknowledged])
  })

  it('returns an empty array for a non-and root node', () => {
    const node: FilterNode = { type: 'or', children: [name, alias] }

    expect(getTopLevelConditions(node)).toStrictEqual([])
  })
})
