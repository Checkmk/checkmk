/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import CmkKpiStatCard from './CmkKpiStatCard.vue'

export default CmkKpiStatCard
export type {
  CmkKpiStatCardProps,
  ComparisonBasis,
  KpiDelta,
  KpiDeltaConfig,
  KpiRangeLimits,
  KpiState,
  KpiStateSeverity,
  KpiValueRange,
  SparkHeightMode,
  TimestampedSample
} from './types'
