/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import {
  configRows,
  hasContextFacts,
  labelEntries,
  topologyGroups
} from '@/maps/map/detail/contextFacts'

import { aDetails } from '../../support/fixtures'

type TranslateFn = ReturnType<typeof usei18n>['_t']

const _t: TranslateFn = (message) => untranslated(message)

describe('configRows', () => {
  it('states nothing at all before the details have arrived', () => {
    expect(configRows(null, _t)).toEqual([])
  })

  it('leaves out the 24x7 notification period, which says nothing', () => {
    const rows = configRows(
      aDetails({ type: 'service', host_name: 'web01', notification_period: '24X7' }),
      _t
    )
    expect(rows.map((row) => row.label)).not.toContain('Notif. period')
  })

  it('tones the notification period while the check is outside it', () => {
    const rows = configRows(
      aDetails({
        type: 'service',
        host_name: 'web01',
        notification_period: 'workhours',
        in_notification_period: false
      }),
      _t
    )
    expect(rows.find((row) => row.label === 'Notif. period')?.tone).toBe('warn')
  })

  it('states the latency in milliseconds, where the site measured one', () => {
    const rows = configRows(aDetails({ type: 'service', host_name: 'web01', latency: 0.0123 }), _t)
    expect(rows.find((row) => row.label === 'Latency')?.value).toBe('12 ms')
  })
})

describe('topologyGroups', () => {
  it('marks parents and children as host lists, and the group memberships not', () => {
    const groups = topologyGroups(
      aDetails({
        type: 'host',
        host_name: 'web01',
        parents: ['gw01'],
        children: ['app01'],
        host_groups: ['linux'],
        contact_groups: ['ops']
      }),
      _t
    )
    expect(groups.map((group) => [group.label, group.isHostList ?? false])).toEqual([
      ['Parents', true],
      ['Children', true],
      ['Host groups', false],
      ['Contact groups', false]
    ])
  })

  it('leaves out every group that is empty', () => {
    expect(topologyGroups(aDetails({ type: 'host', host_name: 'web01' }), _t)).toEqual([])
  })
})

describe('hasContextFacts', () => {
  it('is false for details that carry nothing worth a tab', () => {
    expect(hasContextFacts(aDetails({ type: 'host', host_name: 'web01' }), _t)).toBe(false)
  })

  it('is true as soon as there is a single label', () => {
    const details = aDetails({ type: 'host', host_name: 'web01', labels: { env: 'prod' } })
    expect(labelEntries(details)).toEqual([['env', 'prod']])
    expect(hasContextFacts(details, _t)).toBe(true)
  })

  it('is true for a check command alone', () => {
    expect(
      hasContextFacts(
        aDetails({ type: 'service', host_name: 'web01', check_command: 'check_mk-cpu.loads' }),
        _t
      )
    ).toBe(true)
  })
})
