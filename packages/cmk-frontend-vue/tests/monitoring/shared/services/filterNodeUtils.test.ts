/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { ConditionNode, FilterNode } from '@/monitoring/shared/api/types'
import {
  filterNodesEqual,
  getTopLevelConditions,
  setCondition
} from '@/monitoring/shared/services/filterNodeUtils'

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

describe('filterNodesEqual', () => {
  it('treats two undefined filters as equal', () => {
    expect(filterNodesEqual(undefined, undefined)).toBe(true)
  })

  it('treats a defined filter and undefined as unequal', () => {
    expect(filterNodesEqual(name, undefined)).toBe(false)
    expect(filterNodesEqual(undefined, name)).toBe(false)
  })

  it('considers identical bare conditions equal', () => {
    expect(filterNodesEqual(name, { ...name })).toBe(true)
  })

  it('distinguishes conditions that differ in value, op, or field', () => {
    expect(filterNodesEqual(name, { ...name, value: 'other' })).toBe(false)
    expect(filterNodesEqual(name, { ...name, op: 'matches' })).toBe(false)
    expect(filterNodesEqual(name, alias)).toBe(false)
  })

  it('ignores ordering of one_of values', () => {
    const a: FilterNode = { type: 'condition', field: 'state', op: 'one_of', value: ['DOWN', 'UP'] }
    const b: FilterNode = { type: 'condition', field: 'state', op: 'one_of', value: ['UP', 'DOWN'] }

    expect(filterNodesEqual(a, b)).toBe(true)
  })

  it('ignores ordering of and-node children', () => {
    const a: FilterNode = { type: 'and', children: [name, acknowledged] }
    const b: FilterNode = { type: 'and', children: [acknowledged, name] }

    expect(filterNodesEqual(a, b)).toBe(true)
  })

  it('matches a reconstructed preset regardless of child and value ordering', () => {
    const preset: FilterNode = {
      type: 'and',
      children: [
        { type: 'condition', field: 'state', op: 'one_of', value: ['DOWN', 'UNREACHABLE'] },
        acknowledged
      ]
    }
    // As if rebuilt via the column filter: children and one_of values reordered.
    const rebuilt: FilterNode = {
      type: 'and',
      children: [
        acknowledged,
        { type: 'condition', field: 'state', op: 'one_of', value: ['UNREACHABLE', 'DOWN'] }
      ]
    }

    expect(filterNodesEqual(preset, rebuilt)).toBe(true)
  })

  it('distinguishes and-nodes with different children', () => {
    const a: FilterNode = { type: 'and', children: [name, acknowledged] }
    const b: FilterNode = { type: 'and', children: [name, alias] }

    expect(filterNodesEqual(a, b)).toBe(false)
  })
})
