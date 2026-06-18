/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GraphLineQueryAttributes } from 'cmk-shared-typing/typescript/graph_designer'

import type {
  AttributeFilterModel,
  AttributeType,
  ConnectedCondition
} from './attribute-filter/types'

export type AttributeTypeKey = Exclude<AttributeType, null>

export const ATTRIBUTE_TYPE_ORDER: AttributeTypeKey[] = ['resource', 'scope', 'datapoint']

export const KEY_IDENTS: Record<AttributeTypeKey, string> = {
  resource: 'monitored_resource_attributes_keys_backend',
  scope: 'monitored_scope_attributes_keys_backend',
  datapoint: 'monitored_data_point_attributes_keys_backend'
}

export const VALUE_IDENTS: Record<AttributeTypeKey, string> = {
  resource: 'monitored_resource_attributes_values_backend',
  scope: 'monitored_scope_attributes_values_backend',
  datapoint: 'monitored_data_point_attributes_values_backend'
}

export interface ThreeLists {
  resource: GraphLineQueryAttributes
  scope: GraphLineQueryAttributes
  datapoint: GraphLineQueryAttributes
}

export function toModel(lists: ThreeLists, newId: () => string): AttributeFilterModel {
  const out: ConnectedCondition[] = []
  for (const attributeType of ATTRIBUTE_TYPE_ORDER) {
    for (const attr of lists[attributeType]) {
      out.push({
        id: newId(),
        attributeType,
        key: attr.key,
        operator: 'eq',
        value: attr.value,
        connector: out.length === 0 ? null : 'AND'
      })
    }
  }
  return out
}

export function fromModel(model: AttributeFilterModel): ThreeLists {
  const lists: ThreeLists = { resource: [], scope: [], datapoint: [] }
  for (const condition of model) {
    // Skip key-less conditions (a pill still being created).
    if (condition.attributeType === null || !condition.key) {
      continue
    }
    lists[condition.attributeType].push({ key: condition.key, value: condition.value })
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

const CONTEXT_KEYS: Record<AttributeTypeKey, AttrsKey> = {
  resource: 'resource_attributes',
  scope: 'scope_attributes',
  datapoint: 'data_point_attributes'
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
  for (const attributeType of ATTRIBUTE_TYPE_ORDER) {
    const attrs = model
      .filter(
        (c) =>
          c.attributeType === attributeType &&
          c.id !== options.excludeId &&
          c.key !== null &&
          c.key !== '' &&
          c.value !== ''
      )
      .map((c) => ({ key: c.key as string, value: c.value }))
    if (attrs.length > 0) {
      context[CONTEXT_KEYS[attributeType]] = attrs
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
