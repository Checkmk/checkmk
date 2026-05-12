/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { pillLabel } from '@/metric-backend/attribute-filter/pill-label'
import type { AttributeCondition, AttributeType } from '@/metric-backend/attribute-filter/types'

function makeCondition(
  attributeType: AttributeType,
  operator: AttributeCondition['operator'],
  value = ''
): AttributeCondition {
  return { attributeType, key: 'http.method', operator, value }
}

test('attribute-type prefix is rendered', () => {
  expect(pillLabel(makeCondition(null, 'eq', 'GET'))).toBe('http.method is GET')
  expect(pillLabel(makeCondition('resource', 'eq', 'GET'))).toBe('[Resource] http.method is GET')
  expect(pillLabel(makeCondition('scope', 'eq', 'GET'))).toBe('[Scope] http.method is GET')
  expect(pillLabel(makeCondition('datapoint', 'eq', 'GET'))).toBe('[Data point] http.method is GET')
})

test('all string operators render with their human phrase', () => {
  expect(pillLabel(makeCondition(null, 'eq', 'x'))).toBe('http.method is x')
  expect(pillLabel(makeCondition(null, 'neq', 'x'))).toBe('http.method is not x')
  expect(pillLabel(makeCondition(null, 'contains', 'x'))).toBe('http.method contains x')
  expect(pillLabel(makeCondition(null, 'not_contains', 'x'))).toBe('http.method does not contain x')
  expect(pillLabel(makeCondition(null, 'starts_with', 'x'))).toBe('http.method starts with x')
  expect(pillLabel(makeCondition(null, 'not_starts_with', 'x'))).toBe(
    'http.method does not start with x'
  )
  expect(pillLabel(makeCondition(null, 'ends_with', 'x'))).toBe('http.method ends with x')
  expect(pillLabel(makeCondition(null, 'not_ends_with', 'x'))).toBe(
    'http.method does not end with x'
  )
  expect(pillLabel(makeCondition(null, 'regex', '^/api'))).toBe('http.method matches regex ^/api')
  expect(pillLabel(makeCondition(null, 'not_regex', '^/api'))).toBe(
    'http.method does not match regex ^/api'
  )
})

test('existence operators omit the value', () => {
  expect(pillLabel(makeCondition(null, 'exists'))).toBe('http.method exists')
  expect(pillLabel(makeCondition(null, 'not_exists'))).toBe('http.method does not exist')
})
