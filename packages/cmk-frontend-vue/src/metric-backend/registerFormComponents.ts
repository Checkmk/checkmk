/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { registerFormComponents } from '@/form'

import FormDCDMetricBackendFilter from './FormDCDMetricBackendFilter.vue'

export function registerMetricBackendFormComponents(): void {
  registerFormComponents({
    dcd_metric_backend_filter: FormDCDMetricBackendFilter
  })
}
