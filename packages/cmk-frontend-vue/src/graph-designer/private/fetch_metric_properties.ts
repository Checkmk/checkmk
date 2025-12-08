/**
 * Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cmkAjax } from '@/lib/ajax'

export async function fetchMetricColor<OutputType>(
  metricName: string,
  metricType: 'average' | 'min' | 'max' | 'warn' | 'crit'
): Promise<OutputType> {
  return cmkAjax('ajax_fetch_metric_color.py', {
    metric_name: metricName,
    metric_type: metricType
  })
}
