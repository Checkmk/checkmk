/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { groupMembersQuery, stateExclusion } from '@/maps/utils/memberFilter'

import { anObject } from '../support/fixtures'

describe('stateExclusion', () => {
  it('takes the pattern for the state over the one for the members', () => {
    const host = anObject({
      id: 'h',
      type: 'host',
      exclude_members: 'Disk',
      exclude_member_states: 'CPU'
    })

    expect(stateExclusion(host)).toBe('CPU')
  })

  it('falls back to the pattern for the members', () => {
    expect(stateExclusion(anObject({ id: 'g', type: 'hostgroup', exclude_members: 'web' }))).toBe(
      'web'
    )
  })

  it('has none for an object the daemon leaves no members out of', () => {
    expect(stateExclusion(anObject({ id: 's', type: 'service', exclude_members: 'x' }))).toBeNull()
  })
})

describe('groupMembersQuery', () => {
  it('leaves out the hosts of a host group that match', () => {
    expect(groupMembersQuery('hostgroup', 'web', '^test-')).toEqual({
      objectTypes: 'host',
      objectFilter: 'Filter: groups >= web\nFilter: name !~~ ^test-\n'
    })
  })

  it("keeps a host group's hosts when the pattern names services", () => {
    expect(groupMembersQuery('hostgroup', 'web', 'web-01~~CPU')).toBeNull()
  })

  it('leaves out the services of a service group whose host and service match', () => {
    expect(groupMembersQuery('servicegroup', 'http', 'web-01~~CPU')?.objectFilter).toBe(
      'Filter: groups >= http\nFilter: host_name !~~ web-01\nFilter: description !~~ CPU\nOr: 2\n'
    )
  })

  it('refuses a pattern that would add a query line', () => {
    expect(groupMembersQuery('hostgroup', 'web', 'x\rOr: 2')).toBeNull()
    expect(groupMembersQuery('hostgroup', 'web', 'x\\nOr: 2')).toBeNull()
  })
})
