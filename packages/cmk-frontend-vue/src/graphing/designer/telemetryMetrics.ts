/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ServiceModel } from '@/mode-custom-services/types'

import { consolidationToWire } from './consolidation'
import { DEFAULT_TITLE_MACRO, type MetricBackendItem } from './types'

/** The custom-service model prefilled from a designer row, with the row's title as the service name. */
export function customServiceModelFor(item: MetricBackendItem, defaultTitle: string): ServiceModel {
  return {
    metricName: item.metric_name,
    metricTypes: [],
    attributeFilter: item.attribute_filter,
    consolidation: consolidationToWire(item.consolidation_function),
    aggregator: item.aggregator ?? undefined,
    serviceName: item.title.replaceAll(DEFAULT_TITLE_MACRO, defaultTitle),
    hostName: null
  }
}
