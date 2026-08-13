/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Page } from '@ucl/_ucl/types/page'

import UclCmkDonutChart from './CmkDonutChart/UclCmkDonutChart.vue'
import UclCmkTrendChart from './CmkTrendChart/UclCmkTrendChart.vue'

export const pages: Array<Page> = [
  new Page('CmkDonutChart', UclCmkDonutChart),
  new Page('CmkTrendChart', UclCmkTrendChart)
]
