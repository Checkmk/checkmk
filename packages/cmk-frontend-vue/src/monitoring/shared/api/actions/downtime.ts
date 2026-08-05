/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { hostNameQuery } from '@/monitoring/shared/api/actions/query'

export interface ScheduleDowntimeOptions {
  comment: string
  startTime: string
  endTime: string
  /** Downtime duration in minutes. `0` schedules a fixed downtime, a positive value a flexible one. */
  durationMinutes: number
}

export class ScheduleDowntimeApi {
  /**
   * Resolve the child hosts of the given hosts recursively, mirroring the classic downtime
   * dialog's "Set child hosts in downtime" option. A host is a child of `parent` when `parent`
   * is contained in its `parents` list (`parents >= parent` in Livestatus terms).
   */
  public async resolveChildHosts(hostNames: string[]): Promise<string[]> {
    const seen = new Set(hostNames)
    const children: string[] = []
    let frontier = [...hostNames]

    while (frontier.length > 0) {
      const data = unwrap(
        await client.POST('/domain-types/host/collections/all', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: {
            columns: ['name'],
            query: {
              op: 'or',
              expr: frontier.map((name) => ({ op: '>=', left: 'parents', right: name }))
            }
          }
        })
      )
      frontier = data.value
        .map((host) => host.id)
        .filter((name): name is string => name !== undefined && !seen.has(name))
      for (const name of frontier) {
        seen.add(name)
      }
      children.push(...frontier)
    }

    return children
  }

  public async scheduleDowntime(
    hostNames: string[],
    options: ScheduleDowntimeOptions
  ): Promise<void> {
    unwrap(
      await client.POST('/domain-types/downtime/collections/host', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          downtime_type: 'host_by_query',
          query: hostNameQuery(hostNames),
          start_time: options.startTime,
          end_time: options.endTime,
          recur: 'fixed',
          duration: options.durationMinutes,
          comment: options.comment
        }
      })
    )
  }

  public async scheduleServiceDowntime(
    hostName: string,
    serviceDescriptions: string[],
    options: ScheduleDowntimeOptions
  ): Promise<void> {
    unwrap(
      await client.POST('/domain-types/downtime/collections/service', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          downtime_type: 'service',
          host_name: hostName,
          service_descriptions: serviceDescriptions,
          start_time: options.startTime,
          end_time: options.endTime,
          recur: 'fixed',
          duration: options.durationMinutes,
          comment: options.comment
        }
      })
    )
  }
}
