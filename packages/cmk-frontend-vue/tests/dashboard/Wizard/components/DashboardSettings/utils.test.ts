/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import {
  generateUniqueId,
  isIdInUse,
  isValidSnakeCase,
  toSnakeCase
} from '@/dashboard/components/Wizard/components/DashboardSettings/utils'

vi.mock('@/dashboard/utils', () => ({
  dashboardAPI: {
    listDashboardMetadata: vi.fn().mockResolvedValue([
      { name: 'existing_dashboard', owner: 'admin' },
      { name: 'another_dashboard', owner: 'admin' },
      { name: 'guest_dashboard', owner: 'guest' },
      { name: 'guest_dashboard_1', owner: 'guest' }
    ])
  }
}))

describe('toSnakeCase', () => {
  it.each([
    ['camelCase', 'camel_case'],
    ['PascalCase', 'pascal_case'],
    ['My New Dashboard', 'my_new_dashboard'],
    ['some-dashboard--name!', 'some_dashboard_name_'],
    ['already_snake_case', 'already_snake_case'],
    ['dashboard', 'dashboard'],
    ['', '']
  ])('converts %j to %j', (input, expected) => {
    expect(toSnakeCase(input)).toBe(expected)
  })
})

describe('isValidSnakeCase', () => {
  it.each([
    ['valid_snake_case', true],
    ['dashboard', true],
    ['my_dashboard_123', true],
    ['_leading', true],
    ['Invalid', false],
    ['not-valid', false],
    ['has spaces', false],
    ['', false]
  ])('%j returns %s', (input, expected) => {
    expect(isValidSnakeCase(input)).toBe(expected)
  })
})

describe('isIdInUse', () => {
  it('returns true when the ID is owned by the given owner', async () => {
    expect(await isIdInUse('admin', 'existing_dashboard')).toBe(true)
  })

  it('returns false when the ID is not owned by the given owner', async () => {
    expect(await isIdInUse('guest', 'existing_dashboard')).toBe(false)
  })

  it('returns false when the ID does not exist at all', async () => {
    expect(await isIdInUse('admin', 'nonexistent_dashboard')).toBe(false)
  })

  it('returns false when the ID matches the ignoreId', async () => {
    expect(await isIdInUse('admin', 'existing_dashboard', 'existing_dashboard')).toBe(false)
  })

  it('returns true when the ID is in use and ignoreId is different', async () => {
    expect(await isIdInUse('admin', 'existing_dashboard', 'other_id')).toBe(true)
  })

  it('returns false for an owner with no dashboards', async () => {
    expect(await isIdInUse('nobody', 'existing_dashboard')).toBe(false)
  })
})

describe('generateUniqueId', () => {
  it('returns the baseId when it is not in use', async () => {
    expect(await generateUniqueId('admin', 'new_dashboard')).toBe('new_dashboard')
  })

  it('appends _1 when the baseId is already in use', async () => {
    expect(await generateUniqueId('admin', 'existing_dashboard')).toBe('existing_dashboard_1')
  })

  it('appends _2 when both baseId and baseId_1 are in use', async () => {
    expect(await generateUniqueId('guest', 'guest_dashboard')).toBe('guest_dashboard_2')
  })

  it('returns the baseId when it matches the ignoreId', async () => {
    expect(await generateUniqueId('admin', 'existing_dashboard', 'existing_dashboard')).toBe(
      'existing_dashboard'
    )
  })

  it('returns the baseId for a different owner even if it exists', async () => {
    expect(await generateUniqueId('nobody', 'existing_dashboard')).toBe('existing_dashboard')
  })
})
