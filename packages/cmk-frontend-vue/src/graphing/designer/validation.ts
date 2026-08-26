/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type FilterDefinitions, configuredFilters } from 'cmk-ui-library/components/filter'

import { type ValidationIssue, validateFormula } from './calculation/formula'
import type { DesignerItem, DraftRRDQueryItem } from './drafts'
import { type GraphItem, type ItemId, domainOf, isFormula } from './types'

/** An API field a source must carry before it can be saved. */
type RequiredField = 'host_name' | 'service_name' | 'metric_name' | 'value'

const QUERY_FILTER_SECTIONS = [
  { category: 'host', field: 'host_filter' },
  { category: 'service', field: 'service_filter' }
] as const

/** A filter section of a query that needs at least one filter. */
type FilterField = (typeof QUERY_FILTER_SECTIONS)[number]['field']

type FormulaIssueCode = ValidationIssue['code'] | 'ref-incomplete'

type FieldIssue =
  | { field: 'title' | RequiredField; code: 'required' }
  | { field: FilterField; code: 'filter-required' }
  | { field: 'value' | 'consolidation_function'; code: 'not-finite' }
  | {
      field: 'consolidation_function'
      code: 'lookback-too-small' | 'percentile-out-of-range' | 'thresholds-unordered'
    }

type FormulaIssue = { field: 'ast'; code: FormulaIssueCode; ref: ItemId }

export type RowIssue = { id: ItemId } & (FieldIssue | FormulaIssue)

export type RowField = RowIssue['field']

function isFilled(value: string | null): boolean {
  return value !== null && value.trim() !== ''
}

function isEntered(value: number | null): boolean {
  return value !== null && !Number.isNaN(value)
}

function requiredFieldStates(item: DesignerItem): [RequiredField, boolean][] {
  switch (item.type) {
    case 'rrd_metric':
    case 'scalar':
      return [
        ['host_name', isFilled(item.host_name)],
        ['service_name', isFilled(item.service_name)],
        ['metric_name', isFilled(item.metric_name)]
      ]
    case 'rrd_query':
    case 'metric_backend':
      return [['metric_name', isFilled(item.metric_name)]]
    case 'constant':
      return [['value', isEntered(item.value)]]
    case 'rrd_formula':
      return []
  }
}

/** The required fields this source has yet to fill in, in form order. */
function missingRequiredFields(item: DesignerItem): RequiredField[] {
  return requiredFieldStates(item).flatMap(([field, entered]) => (entered ? [] : [field]))
}

/** The filter sections of a query that hold no fully configured filter yet. */
function missingQueryFilters(
  item: DraftRRDQueryItem,
  filterDefinitions: FilterDefinitions | null
): RowIssue[] {
  const categories = new Set(
    configuredFilters(item.context, filterDefinitions ?? {}).map(
      (definition) => definition.extensions.info
    )
  )
  return QUERY_FILTER_SECTIONS.filter(({ category }) => !categories.has(category)).map(
    ({ field }): RowIssue => ({ id: item.id, field, code: 'filter-required' })
  )
}

function consolidationIssues(
  id: ItemId,
  consolidation: Extract<DesignerItem, { type: 'metric_backend' }>['consolidation_function']
): RowIssue[] {
  const issues: RowIssue[] = []
  // Negated comparisons so a NaN, which loses every comparison, still counts as out of range.
  if (!(consolidation.lookback_seconds >= 1)) {
    issues.push({ id, field: 'consolidation_function', code: 'lookback-too-small' })
  }
  if (
    consolidation.type === 'histogram_quantile' &&
    !(consolidation.percentile >= 0 && consolidation.percentile <= 100)
  ) {
    issues.push({ id, field: 'consolidation_function', code: 'percentile-out-of-range' })
  }
  if (
    consolidation.type === 'histogram_fraction_below' &&
    !Number.isFinite(consolidation.threshold)
  ) {
    issues.push({ id, field: 'consolidation_function', code: 'not-finite' })
  }
  if (
    consolidation.type === 'histogram_fraction_between' &&
    !(consolidation.lower_threshold < consolidation.upper_threshold)
  ) {
    issues.push({ id, field: 'consolidation_function', code: 'thresholds-unordered' })
  }
  return issues
}

/** What blocks this source on its own, ignoring how it relates to the others. */
export function validateRow(
  item: DesignerItem,
  filterDefinitions: FilterDefinitions | null
): RowIssue[] {
  const issues: RowIssue[] = []
  if (item.title.trim() === '') {
    issues.push({ id: item.id, field: 'title', code: 'required' })
  }
  if (item.type === 'rrd_query') {
    issues.push(...missingQueryFilters(item, filterDefinitions))
  }
  for (const field of missingRequiredFields(item)) {
    issues.push({ id: item.id, field, code: 'required' })
  }
  if (
    item.type === 'constant' &&
    (item.value === Number.POSITIVE_INFINITY || item.value === Number.NEGATIVE_INFINITY)
  ) {
    issues.push({ id: item.id, field: 'value', code: 'not-finite' })
  }
  if (item.type === 'metric_backend') {
    issues.push(...consolidationIssues(item.id, item.consolidation_function))
  }
  return issues
}

/** Narrows a source the rules accept to the shape the API takes. */
export function isValid(
  item: DesignerItem,
  filterDefinitions: FilterDefinitions | null
): item is GraphItem {
  return validateRow(item, filterDefinitions).length === 0
}

/** Every source's own blockers, plus the formula rules that span sources. */
export function validateDesign(
  items: readonly DesignerItem[],
  filterDefinitions: FilterDefinitions | null
): RowIssue[] {
  const issues = items.flatMap((item) => validateRow(item, filterDefinitions))
  const valid = items.filter((item): item is GraphItem => isValid(item, filterDefinitions))
  const known = new Set(items.map((item) => item.id))

  for (const item of items) {
    if (!isFormula(item)) {
      continue
    }
    for (const issue of validateFormula(item.ast, valid, domainOf(item.type), item.id)) {
      // `validateFormula` only sees the sources the rules accept, so a reference to one that
      // exists but is still being filled in reaches it as unknown.
      const incompleteRef = issue.code === 'unknown-ref' && known.has(issue.id)
      issues.push({
        id: item.id,
        field: 'ast',
        code: incompleteRef ? 'ref-incomplete' : issue.code,
        ref: issue.id
      })
    }
  }
  return issues
}
