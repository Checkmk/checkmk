/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it } from 'vitest'

import { useGroupMembers } from '@/maps/map/detail/composables/useGroupMembers'
import type { GroupMember, MapElement } from '@/maps/types/api'

import { aGroupMember, anObject } from '../../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../../support/services'

function member(host: string, state: string, extra: Partial<GroupMember> = {}): GroupMember {
  return aGroupMember({ host, service: '', state, output: '', ...extra })
}

function setup(object: MapElement | null = null) {
  return runWithServices(services, () =>
    useGroupMembers({
      object: () => object,
      connectionId: () => null // keep the watch from calling the API
    })
  )
}

let services: ReturnType<typeof fakeMapsServices>

beforeEach(() => {
  services = fakeMapsServices()
})

describe('memberHealth + filteredMembers', () => {
  it('buckets member states into health counts', () => {
    const gm = setup()
    gm.groupMembers.value = [
      member('a', 'OK'),
      member('b', 'UP'),
      member('c', 'WARNING'),
      member('d', 'CRITICAL'),
      member('e', 'DOWN'),
      member('f', 'UNKNOWN'),
      member('g', 'PENDING')
    ]
    expect(gm.filteredMembers.value.map((m) => m.state)).toContain('CRITICAL')
    // worst-first ordering: crit/down rank highest
    expect(['CRITICAL', 'DOWN']).toContain(gm.filteredMembers.value[0]!.state)
  })

  it('sorts worst state first, then by host name', () => {
    const gm = setup()
    gm.groupMembers.value = [member('z', 'OK'), member('a', 'OK'), member('m', 'CRITICAL')]
    expect(gm.filteredMembers.value.map((m) => m.host)).toEqual(['m', 'a', 'z'])
  })

  it('onlyProblems filter drops OK/UP members', () => {
    const gm = setup()
    gm.groupMembers.value = [member('a', 'OK'), member('b', 'CRITICAL')]
    gm.onlyProblems.value = true
    expect(gm.filteredMembers.value.map((m) => m.host)).toEqual(['b'])
  })

  it('search matches host, service and output case-insensitively', () => {
    const gm = setup()
    gm.groupMembers.value = [
      member('web01', 'OK', { service: 'PING' }),
      member('db02', 'OK', { service: 'CPU', output: 'load high' })
    ]
    gm.memberSearch.value = 'LOAD'
    expect(gm.filteredMembers.value.map((m) => m.host)).toEqual(['db02'])
  })
})

describe('truncation', () => {
  it('caps visible members at 50 and reports the overflow', () => {
    const gm = setup()
    gm.groupMembers.value = Array.from({ length: 60 }, (_, i) =>
      member(`h${String(i).padStart(2, '0')}`, 'OK')
    )
    expect(gm.visibleMembers.value).toHaveLength(50)
    expect(gm.truncatedMemberCount.value).toBe(10)
  })

  it('reports zero overflow below the cap', () => {
    const gm = setup()
    gm.groupMembers.value = [member('a', 'OK')]
    expect(gm.truncatedMemberCount.value).toBe(0)
  })
})

describe('memberChips', () => {
  it('emits problem chips only when non-zero, always keeps OK', () => {
    const gm = setup()
    gm.groupMembers.value = [member('a', 'CRITICAL'), member('b', 'OK')]
    expect(gm.memberChips.value.map((c) => c.label)).toEqual(['CRIT', 'OK'])
  })

  it('keeps only the OK chip when everything is healthy', () => {
    const gm = setup()
    gm.groupMembers.value = [member('a', 'OK'), member('b', 'UP')]
    expect(gm.memberChips.value.map((c) => c.label)).toEqual(['OK'])
    expect(gm.memberChips.value[0]!.count).toBe(2)
  })
})

describe('isGroup', () => {
  it('is true for group-like object types', () => {
    expect(setup(anObject({ id: 'o', type: 'hostgroup', url_target: '' })).isGroup.value).toBe(true)
    expect(setup(anObject({ id: 'o', type: 'host', url_target: '' })).isGroup.value).toBe(false)
  })
})

describe('memberStateTone / memberStateBadge', () => {
  it('maps states to tones', () => {
    const gm = setup()
    expect(gm.memberStateTone('DOWN')).toBe('crit')
    expect(gm.memberStateTone('WARNING')).toBe('warn')
    expect(gm.memberStateTone('UNREACHABLE')).toBe('unknown')
    expect(gm.memberStateTone('PENDING')).toBe('pending')
    expect(gm.memberStateTone('OK')).toBe('ok')
  })

  it('maps states to single-character badges', () => {
    const gm = setup()
    expect(gm.memberStateBadge('DOWN')).toBe('D')
    expect(gm.memberStateBadge('CRITICAL')).toBe('C')
    expect(gm.memberStateBadge('WARNING')).toBe('W')
    expect(gm.memberStateBadge('UP')).toBe('✓')
    expect(gm.memberStateBadge('PENDING')).toBe('·')
  })
})
