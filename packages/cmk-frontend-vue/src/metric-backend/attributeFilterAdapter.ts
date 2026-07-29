/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  AttributeFilter,
  AttributeFilterContains as SharedAttributeFilterContains,
  AttributeFilterEndsWith as SharedAttributeFilterEndsWith,
  AttributeFilterEquals as SharedAttributeFilterEquals,
  AttributeFilterExists as SharedAttributeFilterExists,
  AttributeFilterRegex as SharedAttributeFilterRegex,
  AttributeFilterStartsWith as SharedAttributeFilterStartsWith
} from 'cmk-shared-typing/typescript/attribute_filter'

import {
  type AttributeFilterModel,
  type AttributeKind,
  type Condition,
  type Operator,
  isConditionValid
} from './attribute-filter/types'

// Flat key/value attribute list, as the autocomplete REST context and readonly rendering use it.
type GraphLineQueryAttributes = Array<{ key: string; value: string }>

// Pill kinds match the shared model's kinds verbatim, so a condition's kind crosses unchanged.
export type AttributeKindKey = Exclude<AttributeKind, null>

export const ATTRIBUTE_KIND_ORDER: AttributeKindKey[] = ['resource', 'scope', 'data_point']

type PositiveLeaf =
  | SharedAttributeFilterEquals
  | SharedAttributeFilterContains
  | SharedAttributeFilterStartsWith
  | SharedAttributeFilterEndsWith
  | SharedAttributeFilterRegex
  | SharedAttributeFilterExists
type SharedLeaf = PositiveLeaf | { type: 'not'; condition: PositiveLeaf }
type AttributeKey = SharedAttributeFilterEquals['key']

// `satisfies` forces an entry per PositiveLeaf type; a new leaf type breaks the build until mapped.
const WIRE_TYPE_TO_OPERATOR = {
  equals: 'eq',
  contains: 'contains',
  starts_with: 'starts_with',
  ends_with: 'ends_with',
  regex: 'regex',
  exists: 'exists'
} as const satisfies Record<PositiveLeaf['type'], Operator>

// Every operator paired with its negation; the wire encodes a negation as not(<positive>).
const NEGATION_PAIRS: readonly (readonly [Operator, Operator])[] = [
  ['eq', 'neq'],
  ['contains', 'not_contains'],
  ['starts_with', 'not_starts_with'],
  ['ends_with', 'not_ends_with'],
  ['regex', 'not_regex'],
  ['exists', 'not_exists']
]

function negationOf(operator: Operator): Operator | undefined {
  return NEGATION_PAIRS.find(([positive]) => positive === operator)?.[1]
}

function positiveOf(operator: Operator): Operator | undefined {
  return NEGATION_PAIRS.find(([, negated]) => negated === operator)?.[0]
}

function isPositiveLeaf(filter: AttributeFilter): filter is PositiveLeaf {
  return filter.type in WIRE_TYPE_TO_OPERATOR
}

function assertLeaf(filter: AttributeFilter): SharedLeaf {
  // The pill UI only represents an OR of ANDs; deeper nesting has no pill form.
  if (isPositiveLeaf(filter)) {
    return filter
  }
  if (filter.type === 'not' && isPositiveLeaf(filter.condition)) {
    return { type: 'not', condition: filter.condition }
  }
  throw new Error(`attribute filter is not in disjunctive normal form: ${filter.type}`)
}

function positiveLeaf(operator: Operator, key: AttributeKey, value: string): PositiveLeaf {
  switch (operator) {
    case 'eq':
      return { type: 'equals', key, value }
    case 'contains':
      return { type: 'contains', key, value }
    case 'starts_with':
      return { type: 'starts_with', key, value }
    case 'ends_with':
      return { type: 'ends_with', key, value }
    case 'regex':
      return { type: 'regex', key, value }
    case 'exists':
      return { type: 'exists', key }
    default:
      throw new Error(`attribute-filter operator '${operator}' has no backend representation`)
  }
}

function conditionToLeaf(condition: Condition): SharedLeaf {
  if (condition.attributeKind === null || !condition.key) {
    throw new Error('cannot encode an incomplete attribute-filter condition')
  }
  const key = { kind: condition.attributeKind, name: condition.key }
  const positive = positiveOf(condition.operator)
  if (positive !== undefined) {
    return { type: 'not', condition: positiveLeaf(positive, key, condition.value) }
  }
  return positiveLeaf(condition.operator, key, condition.value)
}

// An empty model becomes an empty AND, which the backend treats as "match everything".
export function toAttributeFilter(model: AttributeFilterModel): AttributeFilter {
  const disjuncts: AttributeFilter[] = model
    .map((group) => group.conditions.filter(isConditionValid).map(conditionToLeaf))
    .filter((conjuncts) => conjuncts.length > 0)
    .map((conjuncts) => (conjuncts.length === 1 ? conjuncts[0]! : { type: 'and', conjuncts }))
  if (disjuncts.length === 0) {
    return { type: 'and', conjuncts: [] }
  }
  return disjuncts.length === 1 ? disjuncts[0]! : { type: 'or', disjuncts }
}

function leafToCondition(leaf: SharedLeaf, newId: () => string): Condition {
  const positive = leaf.type === 'not' ? leaf.condition : leaf
  const operator = WIRE_TYPE_TO_OPERATOR[positive.type]
  return {
    id: newId(),
    attributeKind: positive.key.kind,
    key: positive.key.name,
    operator: leaf.type === 'not' ? negationOf(operator)! : operator,
    value: 'value' in positive ? positive.value : ''
  }
}

export function fromAttributeFilter(
  filter: AttributeFilter,
  newId: () => string
): AttributeFilterModel {
  const disjuncts = filter.type === 'or' ? filter.disjuncts : [filter]
  return disjuncts
    .map((disjunct) => {
      const leaves =
        disjunct.type === 'and' ? disjunct.conjuncts.map(assertLeaf) : [assertLeaf(disjunct)]
      return { id: newId(), conditions: leaves.map((leaf) => leafToCondition(leaf, newId)) }
    })
    .filter((group) => group.conditions.length > 0)
}

export const KEY_IDENTS: Record<AttributeKindKey, string> = {
  resource: 'monitored_resource_attributes_keys_backend',
  scope: 'monitored_scope_attributes_keys_backend',
  data_point: 'monitored_data_point_attributes_keys_backend'
}

export const VALUE_IDENTS: Record<AttributeKindKey, string> = {
  resource: 'monitored_resource_attributes_values_backend',
  scope: 'monitored_scope_attributes_values_backend',
  data_point: 'monitored_data_point_attributes_values_backend'
}

// Display-only grouping of the flat filter model by attribute kind (readonly rendering).
export interface ThreeLists {
  resource: GraphLineQueryAttributes
  scope: GraphLineQueryAttributes
  data_point: GraphLineQueryAttributes
}

// The three lists cannot express OR, so all groups flatten together.
export function fromModel(model: AttributeFilterModel): ThreeLists {
  const lists: ThreeLists = { resource: [], scope: [], data_point: [] }
  for (const condition of model.flatMap((group) => group.conditions)) {
    // Skip key-less conditions (a pill still being created).
    if (condition.attributeKind === null || !condition.key) {
      continue
    }
    lists[condition.attributeKind].push({ key: condition.key, value: condition.value })
  }
  return lists
}

export interface AutoCompleteContext {
  metric_name?: string
  attribute_key?: string
  resource_attributes?: GraphLineQueryAttributes
  scope_attributes?: GraphLineQueryAttributes
  data_point_attributes?: GraphLineQueryAttributes
  static_resource_attribute_keys?: string[]
}

export interface ContextOptions {
  metricName?: string | null
  staticResourceAttributeKeys?: string[] | null
  attributeKey?: string | null
  excludeId?: string
}

type AttrsKey = 'resource_attributes' | 'scope_attributes' | 'data_point_attributes'

const CONTEXT_KEYS: Record<AttributeKindKey, AttrsKey> = {
  resource: 'resource_attributes',
  scope: 'scope_attributes',
  data_point: 'data_point_attributes'
}

// Exclude the condition being edited (excludeId) so it does not constrain its own
// value suggestions.
export function buildAutocompleteContext(
  model: AttributeFilterModel,
  options: ContextOptions = {}
): AutoCompleteContext {
  const context: AutoCompleteContext = {}
  if (options.metricName) {
    context.metric_name = options.metricName
  }
  const conditions = model.flatMap((group) => group.conditions)
  for (const attributeKind of ATTRIBUTE_KIND_ORDER) {
    const attrs = conditions
      .filter(
        (c) =>
          c.attributeKind === attributeKind &&
          c.id !== options.excludeId &&
          c.key !== null &&
          c.key !== '' &&
          c.value !== ''
      )
      .map((c) => ({ key: c.key as string, value: c.value }))
    if (attrs.length > 0) {
      context[CONTEXT_KEYS[attributeKind]] = attrs
    }
  }
  if (options.attributeKey) {
    context.attribute_key = options.attributeKey
  }
  if (options.staticResourceAttributeKeys) {
    context.static_resource_attribute_keys = options.staticResourceAttributeKeys
  }
  return context
}
