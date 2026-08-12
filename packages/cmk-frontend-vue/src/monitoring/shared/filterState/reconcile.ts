/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConditionNode, FilterField, FilterNode } from '@/monitoring/shared/api/types'

import type { FilterUrlSchema, FilterUrlState, Problem, RawFilterUrlState } from './types'

/** Search text is capped rather than rejected outright - a long paste is a user mistake, not an attack. */
const MAX_SEARCH_LENGTH = 300

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function reconcileCondition(
  value: Record<string, unknown>,
  schema: FilterUrlSchema
): ConditionNode | undefined {
  const { field, op } = value
  if (typeof field !== 'string' || !schema.filterableFields.has(field as FilterField)) {
    return undefined
  }
  if (typeof op !== 'string' || !('value' in value)) {
    return undefined
  }
  return { type: 'condition', field, op, value: value.value } as ConditionNode
}

/**
 * Recursively validates a decoded value against the {@link FilterNode} shape,
 * dropping whatever does not fit - an unknown field, a malformed branch - and
 * collapsing an emptied `and`/`or` rather than keeping a hollow node. `op` and
 * a leaf's `value` are trusted once its `field` is known: replicating the
 * full per-field condition schema here would duplicate what the API already
 * validates, and a rejected request degrades the same way an invalid sort
 * does (see `MonitoringService.fetch`'s error handling) rather than crashing.
 */
function reconcileNode(value: unknown, schema: FilterUrlSchema): FilterNode | undefined {
  if (!isPlainObject(value) || typeof value.type !== 'string') {
    return undefined
  }
  switch (value.type) {
    case 'and':
    case 'or': {
      if (!Array.isArray(value.children)) {
        return undefined
      }
      const children = value.children
        .map((child: unknown) => reconcileNode(child, schema))
        .filter((child): child is FilterNode => child !== undefined)
      if (children.length === 0) {
        return undefined
      }
      return children.length === 1 ? children[0] : ({ type: value.type, children } as FilterNode)
    }
    case 'not': {
      const child = reconcileNode(value.child, schema)
      return child === undefined ? undefined : ({ type: 'not', child } as FilterNode)
    }
    case 'condition':
      return reconcileCondition(value, schema)
    default:
      return undefined
  }
}

/**
 * Strips control characters and caps the length; never rejects search text
 * outright. Counts and cuts code points, not UTF-16 units: slicing a string
 * could split a surrogate pair, and the lone surrogate left behind would make
 * `encodeQueryValue` throw when this state is written back to the URL.
 */
function reconcileSearch(raw: string): string {
  return Array.from(raw)
    .filter((char) => {
      const code = char.codePointAt(0) ?? 0
      return code >= 0x20 && code !== 0x7f
    })
    .slice(0, MAX_SEARCH_LENGTH)
    .join('')
}

/**
 * Validates a decoded {@link RawFilterUrlState} against a table's filter
 * schema. Every rule drops the offending fragment, keeps the rest, records a
 * {@link Problem}, and never throws - a hand-edited or stale bookmark must
 * degrade, not error.
 */
export function reconcile(
  raw: RawFilterUrlState,
  schema: FilterUrlSchema
): { state: FilterUrlState; problems: Problem[] } {
  const problems: Problem[] = []

  let filter: FilterNode | undefined
  if (raw.filter !== undefined) {
    filter = reconcileNode(raw.filter, schema)
    if (filter === undefined) {
      problems.push({
        message:
          'filter param was malformed or named a column this table does not filter; cleared it'
      })
    }
  }

  const search = reconcileSearch(raw.search)
  if (search !== raw.search) {
    problems.push({ message: 'q param contained control characters or was too long; sanitised it' })
  }

  return { state: { filter, search }, problems }
}
