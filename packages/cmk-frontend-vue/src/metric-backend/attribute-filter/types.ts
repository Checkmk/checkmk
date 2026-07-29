/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type AttributeKind = 'resource' | 'scope' | 'data_point' | null

export const STRING_OPERATORS = [
  'eq',
  'neq',
  'contains',
  'not_contains',
  'starts_with',
  'not_starts_with',
  'ends_with',
  'not_ends_with',
  'regex',
  'not_regex'
] as const

export type StringOperator = (typeof STRING_OPERATORS)[number]

export const EXISTENCE_OPERATORS = ['exists', 'not_exists'] as const

export type ExistenceOperator = (typeof EXISTENCE_OPERATORS)[number]

export type Operator = StringOperator | ExistenceOperator

export const SUPPORTED_OPERATORS: Operator[] = [
  'eq',
  'neq',
  'contains',
  'not_contains',
  'starts_with',
  'not_starts_with',
  'ends_with',
  'not_ends_with',
  'exists',
  'not_exists'
]

export function operatorTakesValue(operator: Operator): operator is StringOperator {
  return STRING_OPERATORS.includes(operator as StringOperator)
}

export function isOperator(value: string): value is Operator {
  return (
    STRING_OPERATORS.includes(value as StringOperator) ||
    EXISTENCE_OPERATORS.includes(value as ExistenceOperator)
  )
}

export interface AttributeCondition {
  attributeKind: AttributeKind
  key: string | null
  operator: Operator
  value: string
}

export function isConditionValid(c: AttributeCondition): boolean {
  return (
    c.key !== '' &&
    c.key !== null &&
    c.attributeKind !== null &&
    !(operatorTakesValue(c.operator) && c.value === '')
  )
}

export interface Condition extends AttributeCondition {
  id: string
}

// One AND-joined clause.
export interface ConditionGroup {
  id: string
  conditions: Condition[]
}

// OR of AND groups (disjunctive normal form).
export type AttributeFilterModel = ConditionGroup[]
