/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConditionNode, FilterField, FilterNode } from '@/monitoring/shared/api/types'

function isCondition(node: FilterNode): node is ConditionNode {
  return node.type === 'condition'
}

function getTopChildren(node: FilterNode): FilterNode[] {
  if (node.type === 'and') {
    return node.children as FilterNode[]
  }
  return [node]
}

/**
 * Immutably replace, add, or remove the top-level condition for a field in a flat AND node.
 * Passing `undefined` for condition removes it.
 */
export function setCondition(
  node: FilterNode | undefined,
  field: FilterField,
  condition: ConditionNode | undefined
): FilterNode | undefined {
  const children = (node !== undefined ? getTopChildren(node) : []).filter(
    (c) => !(isCondition(c) && c.field === field)
  )
  const next = condition !== undefined ? [...children, condition] : children
  if (next.length === 0) {
    return undefined
  }
  if (next.length === 1) {
    return next[0]!
  }
  return { type: 'and', children: next }
}

/** Return all top-level ConditionNodes from a FilterNode. */
export function getTopLevelConditions(node: FilterNode): ConditionNode[] {
  return getTopChildren(node).filter(isCondition)
}
