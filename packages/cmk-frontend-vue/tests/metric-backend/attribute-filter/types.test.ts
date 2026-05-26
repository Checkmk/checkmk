/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { isConditionValid } from '@/metric-backend/attribute-filter/types'
import type { AttributeCondition } from '@/metric-backend/attribute-filter/types'

function condition(overrides: Partial<AttributeCondition> = {}): AttributeCondition {
  return {
    attributeType: 'resource',
    key: 'service.name',
    operator: 'eq',
    value: 'foo',
    ...overrides
  }
}

describe('isConditionValid', () => {
  test('returns true when all required fields are populated', () => {
    expect(isConditionValid(condition())).toBe(true)
  })

  test.each([['' as const], [null]])('returns false when key is missing (%p)', (key) => {
    expect(isConditionValid(condition({ key }))).toBe(false)
  })

  test('returns false when attributeType is null', () => {
    expect(isConditionValid(condition({ attributeType: null }))).toBe(false)
  })

  test('returns false when a value-taking operator has an empty value', () => {
    expect(isConditionValid(condition({ operator: 'eq', value: '' }))).toBe(false)
    expect(isConditionValid(condition({ operator: 'contains', value: '' }))).toBe(false)
  })

  test('returns true when an existence operator has an empty value', () => {
    expect(isConditionValid(condition({ operator: 'exists', value: '' }))).toBe(true)
    expect(isConditionValid(condition({ operator: 'not_exists', value: '' }))).toBe(true)
  })
})
