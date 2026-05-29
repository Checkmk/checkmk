/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type AttributeType = 'resource' | 'scope' | 'datapoint' | null

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
  attributeType: AttributeType
  key: string | null
  operator: Operator
  value: string
}

export type Connector = 'AND' | 'OR'

export interface ConnectedCondition extends AttributeCondition {
  connector: Connector
  id: string
}

// The first entry's `connector` is semantically meaningless (nothing precedes
// it). The flat array shape is so we can render
// connectors between adjacent pills and introduce OR / AND-grouping without
// churning the data contract. Consumers must ignore `model[0].connector`.
export type AttributeFilterModel = ConnectedCondition[]
