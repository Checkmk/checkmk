/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ServiceRef } from '@/monitoring/shared/api/types'

/** A Livestatus filter matching every host whose `name` is one of `hostNames`. */
export function hostNameQuery(hostNames: string[]) {
  return {
    op: 'or' as const,
    expr: hostNames.map((name) => ({ op: '=' as const, left: 'name', right: name }))
  }
}

function descriptionsByHostName(services: ServiceRef[]): Map<string, string[]> {
  const groups = new Map<string, string[]>()
  for (const service of services) {
    const descriptions = groups.get(service.host.name) ?? []
    descriptions.push(service.description)
    groups.set(service.host.name, descriptions)
  }
  return groups
}

/**
 * A Livestatus filter matching `services`: one branch per host name, ORed, or that branch alone
 * when all services share one host. An empty list yields an `or` without operands.
 *
 * Services are matched by host name and description only: the acknowledge and downtime queries
 * have no site column, so a host name found on several sites matches the services of each.
 */
export function serviceQuery(services: ServiceRef[]) {
  const queries = [...descriptionsByHostName(services)].map(([hostName, descriptions]) =>
    serviceDescriptionQuery(hostName, descriptions)
  )
  const [single, ...others] = queries
  return single !== undefined && others.length === 0 ? single : { op: 'or' as const, expr: queries }
}

/** A Livestatus filter matching the named services of a single host. */
function serviceDescriptionQuery(hostName: string, serviceDescriptions: string[]) {
  return {
    op: 'and' as const,
    expr: [
      { op: '=' as const, left: 'host_name', right: hostName },
      {
        op: 'or' as const,
        expr: serviceDescriptions.map((description) => ({
          op: '=' as const,
          left: 'description',
          right: description
        }))
      }
    ]
  }
}
