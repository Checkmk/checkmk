/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { flatFilterUrlCodec } from '@/monitoring/shared/filterState/codec'
import type { ColumnCondition } from '@/monitoring/shared/services/MonitoringService'
import { mergeQuery } from '@/monitoring/shared/urlQuery'

const PAGE = 'monitor_all_hosts.py'

/**
 * Where the page listing all hosts lives, narrowed to the given condition. The
 * narrowing rides in the same `filter` param the page writes for a filter set by
 * hand, spelled by the same codec - so arriving through a link leaves the page in
 * a state its own filter panel goes on editing.
 */
export function allHostsPageUrl(condition: ColumnCondition): string {
  return `${PAGE}${mergeQuery('', flatFilterUrlCodec.encode({ filter: condition, search: '' }))}`
}
