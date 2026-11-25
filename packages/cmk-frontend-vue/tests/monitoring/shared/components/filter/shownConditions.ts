/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConditionNode, FilterField } from '@/monitoring/shared/api/types'
import type { ColumnFilterDefinition } from '@/monitoring/shared/components/filter/types'

type ConditionOp = ConditionNode['op']

// What a free-text field without `suggest` shows. A string-input with `suggest` shows its picks
// instead, without the hints, and may show other operators; no column of the pages sets `suggest`
// on one, so that case is not covered here.
const STRING_INPUT_OPS: readonly ConditionOp[] = [
  'contains',
  // Shown with a "Regular expression" hint.
  'matches',
  // Shown with an "Exact match" hint, but only with a single value.
  'one_of'
]

/**
 * The operators a column filter of each kind shows when its condition comes from the URL rather
 * than from the user's clicks. The component tests of the kinds check the same operators, but
 * nothing ties this table to them: when a component starts or stops showing an operator, update
 * both. Keyed by kind, so that a new kind fails the type check until it says what it shows.
 *
 * A date-time-range shows only `gte` and `lte`: the pages swap it for a duration filter, which
 * shows `gt` and `lt` too, depending on the timestamp format the user picked.
 */
const SHOWN_OPS: {
  [Kind in ColumnFilterDefinition['type']]: (
    filter: Extract<ColumnFilterDefinition, { type: Kind }>
  ) => [FilterField, readonly ConditionOp[]][]
} = {
  'checkbox-list': (filter) => [[filter.field, ['one_of']]],
  'string-input': (filter) => [[filter.field, STRING_INPUT_OPS]],
  numeric: (filter) => [[filter.field, ['gte', 'lte', 'gt', 'lt', 'eq']]],
  'date-time-range': (filter) => [[filter.field, ['gte', 'lte']]],
  duration: (filter) => [[filter.field, ['gte', 'lte', 'gt', 'lt']]],
  'boolean-group': (filter) => filter.groups.map((group) => [group.field, ['eq']]),
  'checkbox-list-with-flags': (filter) => [
    [filter.field, ['one_of']],
    ...filter.flags.map((flag): [FilterField, readonly ConditionOp[]] => [flag.field, ['eq']])
  ],
  'string-input-with-checkbox-list': (filter) => [
    [filter.field, STRING_INPUT_OPS],
    [filter.checkboxField, ['one_of']]
  ],
  'autocomplete-choice': (filter) => [[filter.field, ['all_of', 'one_of']]],
  'column-visibility': () => [],
  'visual-filter': () => []
}

/**
 * List the conditions a column filter shows, as `field:op`, the form of the shared schema
 * `monitoring/page_filter_condition.json`.
 *
 * The `columns.test.ts` of each page (all-hosts, all-services, host-services) keeps a record of the
 * schema's conditions of that page, typed with `satisfies Record<..., true>`: the type check fails
 * if the record misses a condition of the schema or names one it lacks, and the test fails if the
 * columns show others. The backend builds its links to the page from the schema.
 */
export function listShownConditions(filter: ColumnFilterDefinition): string[] {
  return shownOpsOf(filter).flatMap(([field, ops]) => ops.map((op) => `${field}:${op}`))
}

function shownOpsOf<Kind extends ColumnFilterDefinition['type']>(
  filter: Extract<ColumnFilterDefinition, { type: Kind }>
): [FilterField, readonly ConditionOp[]][] {
  return SHOWN_OPS[filter.type](filter)
}
