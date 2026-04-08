/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import {
  getContactGroups,
  getSites
} from '@/dashboard/components/Wizard/wizards/dashboard-settings/api'

const mockFetchRestAPI = vi.hoisted(() => vi.fn())

vi.mock('@/lib/cmkFetch.ts', () => ({
  fetchRestAPI: mockFetchRestAPI
}))

function mockSuccessResponse(data: { value: Array<{ id: string; title: string }> }) {
  mockFetchRestAPI.mockResolvedValueOnce({
    raiseForStatus: vi.fn().mockResolvedValue(undefined),
    json: vi.fn().mockResolvedValue(data)
  })
}

describe('API functions', () => {
  it('getContactGroups fetches correct URL and maps id to name', async () => {
    mockSuccessResponse({
      value: [
        { id: 'admins', title: 'Administrators' },
        { id: 'ops', title: 'Operations' }
      ]
    })

    const result = await getContactGroups()

    expect(mockFetchRestAPI).toHaveBeenCalledWith(
      'api/unstable/domain-types/contact_group_config/collections/all',
      'GET'
    )
    expect(result).toEqual([
      { name: 'admins', title: 'Administrators' },
      { name: 'ops', title: 'Operations' }
    ])
  })

  it('getSites fetches correct URL and maps id to name', async () => {
    mockSuccessResponse({
      value: [
        { id: 'site1', title: 'Production Site' },
        { id: 'site2', title: 'Staging Site' }
      ]
    })

    const result = await getSites()

    expect(mockFetchRestAPI).toHaveBeenCalledWith(
      'api/unstable/domain-types/site_connection/collections/all',
      'GET'
    )
    expect(result).toEqual([
      { name: 'site1', title: 'Production Site' },
      { name: 'site2', title: 'Staging Site' }
    ])
  })
})
