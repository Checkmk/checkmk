/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterNode, HostRef, ServiceState } from '@/monitoring/shared/api/types'
import { flatFilterUrlCodec } from '@/monitoring/shared/filterState/codec'
import { mergeQuery } from '@/monitoring/shared/urlQuery'

const PAGE = 'monitor_host_services.py'

/**
 * Where the host services page for one host lives, narrowed to the given
 * service states. The narrowing rides in the same `filter` param the page
 * writes for a filter set by hand, spelled by the same codec - so arriving
 * through a link leaves the page in a state its own filter panel goes on
 * editing.
 */
export function hostServicesPageUrl(host: HostRef, states?: readonly ServiceState[]): string {
  const filter: FilterNode | undefined =
    states === undefined
      ? undefined
      : { type: 'condition', field: 'state', op: 'one_of', value: [...states] }
  return `${PAGE}${mergeQuery('', {
    host: host.name,
    site: host.site_id,
    ...flatFilterUrlCodec.encode({ filter, search: '' })
  })}`
}
