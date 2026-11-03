/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { serviceQuery } from '@/monitoring/shared/api/actions/query'
import type { ServiceRef } from '@/monitoring/shared/api/types'

function ref(siteId: string, hostName: string, description: string): ServiceRef {
  return { host: { site_id: siteId, name: hostName }, description }
}

function hostQuery(hostName: string, descriptions: string[]) {
  return {
    op: 'and',
    expr: [
      { op: '=', left: 'host_name', right: hostName },
      {
        op: 'or',
        expr: descriptions.map((description) => ({
          op: '=',
          left: 'description',
          right: description
        }))
      }
    ]
  }
}

describe('serviceQuery', () => {
  test('matches the services of a single host without an enclosing or', () => {
    expect(
      serviceQuery([ref('local', 'web-1', 'CPU load'), ref('local', 'web-1', 'Memory')])
    ).toEqual(hostQuery('web-1', ['CPU load', 'Memory']))
  })

  test('ORs one branch per host for the services of several hosts', () => {
    expect(
      serviceQuery([
        ref('local', 'web-1', 'CPU load'),
        ref('local', 'web-2', 'Memory'),
        ref('local', 'web-1', 'Uptime')
      ])
    ).toEqual({
      op: 'or',
      expr: [hostQuery('web-1', ['CPU load', 'Uptime']), hostQuery('web-2', ['Memory'])]
    })
  })

  test('matches a host name given on two sites in one branch', () => {
    expect(
      serviceQuery([ref('local', 'web-1', 'CPU load'), ref('remote', 'web-1', 'Memory')])
    ).toEqual(hostQuery('web-1', ['CPU load', 'Memory']))
  })

  test('yields an or without operands for no services', () => {
    expect(serviceQuery([])).toEqual({ op: 'or', expr: [] })
  })
})
