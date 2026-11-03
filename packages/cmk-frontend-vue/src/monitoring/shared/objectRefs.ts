/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HostRef, ServiceEntry, ServiceRef } from '@/monitoring/shared/api/types'

/** Just the reference to a host, without the rest an entry of it carries. */
export function hostRefOf(host: HostRef): HostRef {
  return { site_id: host.site_id, name: host.name }
}

/** The reference to the host of a service. */
export function hostRefOfService(service: ServiceEntry): HostRef {
  return { site_id: service.site_id, name: service.host_name }
}

/** The reference to the service of the given description on the given host. */
export function serviceRefOf(host: HostRef, description: string): ServiceRef {
  return { host, description }
}

/**
 * A command picked in a row of services, aimed at the service the command names on the given
 * host. That need not be the row's own service: an agent-based service is rescheduled by
 * rescheduling the host's "Check_MK" service.
 */
export function serviceCommand(
  host: HostRef,
  command: { id: string; target: string }
): { id: string; target: ServiceRef } {
  return { id: command.id, target: serviceRefOf(host, command.target) }
}
