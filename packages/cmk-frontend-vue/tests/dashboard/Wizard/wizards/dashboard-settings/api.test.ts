/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  getContactGroups,
  getSites
} from '@/dashboard/components/Wizard/wizards/dashboard-settings/api'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let getSpy: any

function mockCollection(value: Array<{ id: string; title: string }>) {
  getSpy.mockResolvedValueOnce({
    data: { value },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
}

describe('API functions', () => {
  beforeEach(() => {
    getSpy = vi.spyOn(client, 'GET')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('getContactGroups requests the contact group collection and maps id to name', async () => {
    mockCollection([
      { id: 'admins', title: 'Administrators' },
      { id: 'ops', title: 'Operations' }
    ])

    const result = await getContactGroups()

    expect(getSpy).toHaveBeenCalledWith('/domain-types/contact_group_config/collections/all')
    expect(result).toEqual([
      { name: 'admins', title: 'Administrators' },
      { name: 'ops', title: 'Operations' }
    ])
  })

  it('getSites requests the site connection collection and maps id to name', async () => {
    mockCollection([
      { id: 'site1', title: 'Production Site' },
      { id: 'site2', title: 'Staging Site' }
    ])

    const result = await getSites()

    expect(getSpy).toHaveBeenCalledWith('/domain-types/site_connection/collections/all')
    expect(result).toEqual([
      { name: 'site1', title: 'Production Site' },
      { name: 'site2', title: 'Staging Site' }
    ])
  })
})
