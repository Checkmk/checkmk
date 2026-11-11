/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  AgeCondition,
  ConditionNode,
  FilterField,
  FilterNode
} from '@/monitoring/shared/api/types'

/** A leaf a column funnel owns: a condition on its field, or a relative age bound on it. */
type FieldNode = ConditionNode | AgeCondition

function isFieldNode(node: FilterNode): node is FieldNode {
  return node.type === 'condition' || node.type === 'age'
}

function getTopChildren(node: FilterNode): FilterNode[] {
  if (node.type === 'and') {
    return node.children as FilterNode[]
  }
  return [node]
}

/**
 * Immutably replace, add, or remove the top-level condition(s) for a field in a flat
 * AND node. `value` may itself be an AND of conditions on the same field (e.g. a numeric
 * range's lower and upper bound); its conditions are flattened into the top level so the
 * store keeps a single flat AND. Passing `undefined` removes all conditions for the field.
 */
export function setCondition(
  node: FilterNode | undefined,
  field: FilterField,
  value: FilterNode | undefined
): FilterNode | undefined {
  const others = (node !== undefined ? getTopChildren(node) : []).filter(
    (c) => !(isFieldNode(c) && c.field === field)
  )
  const additions = value !== undefined ? getTopChildren(value) : []
  const next = [...others, ...additions]
  if (next.length === 0) {
    return undefined
  }
  if (next.length === 1) {
    return next[0]!
  }
  return { type: 'and', children: next }
}

/** Return all top-level per-field leaves from a FilterNode. */
export function getTopLevelConditions(node: FilterNode): FieldNode[] {
  return getTopChildren(node).filter(isFieldNode)
}

/**
 * A top-level node a column funnel owns: a per-field leaf, or an OR of such leaves (e.g. status
 * flags combined with OR). Anything nested deeper belongs to no column.
 */
type ColumnNode = FieldNode | { type: 'or'; children: FieldNode[] }

function isColumnNode(node: FilterNode): node is ColumnNode {
  return isFieldNode(node) || (node.type === 'or' && node.children.every(isFieldNode))
}

function leafFields(node: ColumnNode): FilterField[] {
  return isFieldNode(node) ? [node.field] : node.children.map((child) => child.field)
}

function isOwnedBy(node: FilterNode, fields: readonly FilterField[]): boolean {
  return isColumnNode(node) && leafFields(node).every((field) => fields.includes(field))
}

/** The top-level nodes of a flat AND that a column filtering on `fields` owns. */
export function getColumnNodes(node: FilterNode, fields: readonly FilterField[]): FilterNode[] {
  return getTopChildren(node).filter((child) => isOwnedBy(child, fields))
}

/**
 * Immutably replace the nodes a column filtering on `fields` owns in a flat AND by the top-level
 * nodes of `value` (which an AND is flattened into). Passing `undefined` removes them.
 */
export function setColumnNodes(
  node: FilterNode | undefined,
  fields: readonly FilterField[],
  value: FilterNode | undefined
): FilterNode | undefined {
  const next = [
    ...(node !== undefined ? getTopChildren(node) : []).filter((c) => !isOwnedBy(c, fields)),
    ...(value !== undefined ? getTopChildren(value) : []).filter((c) => isOwnedBy(c, fields))
  ]
  return next.length === 0
    ? undefined
    : next.length === 1
      ? next[0]!
      : { type: 'and', children: next }
}

/** Every field the column-owned top-level nodes of a flat AND filter on. */
export function getTopLevelFields(node: FilterNode): FilterField[] {
  return getTopChildren(node).filter(isColumnNode).flatMap(leafFields)
}

type CanonicalNode =
  | { type: 'condition'; field: string; op: string; value: unknown }
  | { type: 'age'; field: string; op: string; seconds: number }
  | { type: 'and' | 'or'; children: CanonicalNode[] }
  | { type: 'not'; child: CanonicalNode }

/**
 * Produce an order-independent canonical form of a filter node: children of
 * `and`/`or` nodes are sorted, and `one_of` value arrays are sorted, so that two
 * filters that differ only in ordering canonicalize to the same shape.
 */
function canonicalize(node: FilterNode): CanonicalNode {
  if (node.type === 'condition') {
    const value = Array.isArray(node.value) ? [...node.value].sort() : node.value
    return { type: 'condition', field: node.field, op: node.op, value }
  }
  if (node.type === 'age') {
    return { type: 'age', field: node.field, op: node.op, seconds: node.seconds }
  }
  if (node.type === 'not') {
    return { type: 'not', child: canonicalize(node.child) }
  }
  const children = node.children
    .map(canonicalize)
    .sort((a, b) => (JSON.stringify(a) < JSON.stringify(b) ? -1 : 1))
  return { type: node.type, children }
}

/**
 * Structural (value-based) equality for filter nodes, independent of child and
 * `one_of` value ordering. Two `undefined` filters are equal; a defined filter
 * is never equal to `undefined`.
 */
export function filterNodesEqual(a: FilterNode | undefined, b: FilterNode | undefined): boolean {
  if (a === b) {
    return true
  }
  if (a === undefined || b === undefined) {
    return false
  }
  return JSON.stringify(canonicalize(a)) === JSON.stringify(canonicalize(b))
}
