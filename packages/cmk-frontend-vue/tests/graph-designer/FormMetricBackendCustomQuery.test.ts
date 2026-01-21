/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import FormMetricBackendCustomQuery from '@/graph-designer/FormMetricBackendCustomQuery.vue'

test('Render FormMetricBackendCustomQuery', () => {
  render(FormMetricBackendCustomQuery, {
    props: {
      aggregationLookback: 0,
      aggregationHistogramPercentile: 0
    }
  })
})
