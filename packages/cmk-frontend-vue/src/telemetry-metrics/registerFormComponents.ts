/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { registerFormComponents } from '@/form'

import FormDCDTelemetryMetricsFilter from './FormDCDTelemetryMetricsFilter.vue'

export function registerTelemetryMetricsFormComponents(): void {
  registerFormComponents({
    dcd_metric_backend_filter: FormDCDTelemetryMetricsFilter
  })
}
