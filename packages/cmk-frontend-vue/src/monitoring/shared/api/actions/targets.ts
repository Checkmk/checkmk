/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ServiceRef } from '@/monitoring/shared/api/types'

/** The services as the monitoring actions take them, each naming the site of its host. */
export function serviceTargets(services: ServiceRef[]) {
  return services.map((service) => ({
    site_id: service.host.site_id,
    host_name: service.host.name,
    name: service.description
  }))
}
