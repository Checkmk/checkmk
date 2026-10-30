/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { MetricInfoApi, type SharedMetricInfoRequest } from '@/maps/api/metricInfo'
import type { MetricInfoResult } from '@/maps/types/api'

const server = useMswServer()

type BulkBody = { entries: { perf_data: string }[] }

function lookup(service: string, perfData: string): SharedMetricInfoRequest {
  return {
    identity: service,
    snapshot: perfData,
    perfData,
    checkCommand: 'check_mk-cpu_loads'
  }
}

function resultFor(perfData: string): MetricInfoResult {
  return {
    perfometer: { label: perfData, rows: [], sides: [], bg_color: '#000' },
    metrics: {}
  }
}

describe('MetricInfoApi', () => {
  it('sends the lookups of one task as a single request', async () => {
    const bodies: BulkBody[] = []
    server.use(
      restApiHttp.post(
        '/domain-types/maps_metric_info/actions/bulk-resolve/invoke',
        async ({ request, response }) => {
          const body = (await request.json()) as BulkBody
          bodies.push(body)
          return response(200).json({
            results: body.entries.map((entry) => resultFor(entry.perf_data))
          })
        }
      )
    )
    const api = new MetricInfoApi()

    const results = await Promise.all([
      api.resolveShared(lookup('CPU load', 'load1=1')),
      api.resolveShared(lookup('Memory', 'load1=2'))
    ])

    expect(bodies.map((body) => body.entries.map((entry) => entry.perf_data))).toEqual([
      ['load1=1', 'load1=2']
    ])
    expect(results.map((result) => result?.perfometer?.label)).toEqual(['load1=1', 'load1=2'])
  })

  it('resolves graphs on their own, with the object they are evaluated for', async () => {
    const hosts: string[] = []
    server.use(
      restApiHttp.post(
        '/domain-types/maps_metric_info/actions/resolve/invoke',
        async ({ request, response }) => {
          hosts.push(((await request.json()) as { host_name: string }).host_name)
          return response(200).json({ ...resultFor('load1=1'), graphs: [] })
        }
      )
    )
    const api = new MetricInfoApi()

    await api.resolveShared({
      ...lookup('CPU load', 'load1=1'),
      graphContext: { hostName: 'heute' }
    })

    expect(hosts).toEqual(['heute'])
  })

  it('asks again on the next tick after a failed request', async () => {
    let calls = 0
    server.use(
      restApiHttp.post(
        '/domain-types/maps_metric_info/actions/bulk-resolve/invoke',
        ({ response }) => {
          calls += 1
          return calls === 1
            ? response.untyped(HttpResponse.json({ status: 503 }, { status: 503 }))
            : response(200).json({ results: [resultFor('load1=1')] })
        }
      )
    )
    const api = new MetricInfoApi()

    expect(await api.resolveShared(lookup('CPU load', 'load1=1'))).toBeNull()
    expect((await api.resolveShared(lookup('CPU load', 'load1=1')))?.perfometer?.label).toBe(
      'load1=1'
    )
  })
})
