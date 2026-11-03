/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { useDashboardFilters } from '@/dashboard/composables/useDashboardFilters'
import type { DashboardFilterContextWithSingleInfos } from '@/dashboard/types/dashboard'

describe('useDashboardFilters', () => {
  it('lets an applied runtime filter replace the dashboard own filter of that id', () => {
    const dashboardFilters = useDashboardFilters(
      ref<DashboardFilterContextWithSingleInfos>({
        restricted_to_single: [],
        uses_infos: [],
        mandatory_context_filters: [],
        filters: {
          host_labels: { host_labels_1_vs_1_vs: 'os:linux' },
          hostregex: { host_regex: 'web' }
        }
      })
    )

    dashboardFilters.handleApplyRuntimeFilters({
      host_labels: { host_labels_1_vs_1_vs: 'os:windows' }
    })

    expect(dashboardFilters.baseFilters.value).toEqual({
      host_labels: { host_labels_1_vs_1_vs: 'os:windows' },
      hostregex: { host_regex: 'web' }
    })
  })
})
