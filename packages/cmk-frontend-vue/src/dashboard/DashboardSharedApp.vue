<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, provide } from 'vue'

import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'

import DashboardComponent from '@/dashboard/components/DashboardComponent.vue'
import SharedDashboardMenuHeader from '@/dashboard/components/DashboardMenuHeader/SharedDashboardMenuHeader.vue'
import { useProvideCmkToken } from '@/dashboard/composables/useCmkToken'
import { useDashboardFilters } from '@/dashboard/composables/useDashboardFilters.ts'
import { useDashboardWidgets } from '@/dashboard/composables/useDashboardWidgets.ts'
import { useProvideIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import { type DashboardKey, DashboardLayout } from '@/dashboard/types/dashboard.ts'
import { urlParamsKey } from '@/dashboard/types/injectionKeys.ts'
import type { SharedDashboardPageProperties } from '@/dashboard/types/page.ts'
import { createDashboardModel } from '@/dashboard/utils.ts'

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

const props = defineProps<SharedDashboardPageProperties>()

const dashboardKey = computed(() => {
  return {
    name: props.dashboard.name,
    owner: props.dashboard.owner
  } as DashboardKey
})

const sharedDashboard = createDashboardModel(props.dashboard.spec, DashboardLayout.RELATIVE_GRID)

// So far, urlParams is only needed and used by the DashboardContentNtop component (ntop.ts)
//         cmkToken only by the DashboardContentFigure component
provide(urlParamsKey, props.url_params)
// TODO: remove this hard coded "0:" once the backend can provide the token version
useProvideCmkToken(`0:${props.token_value}`)
useProvideIsPublicDashboard()
useProvideDashboardConstants(props.dashboard_constants)

const dashboardFilters = useDashboardFilters(computed(() => sharedDashboard.filter_context))
const dashboardWidgets = useDashboardWidgets(computed(() => sharedDashboard.content.widgets))
useProvideMissingRuntimeFiltersAction(dashboardFilters.areAllMandatoryFiltersApplied, () => {})
</script>

<template>
  <CmkErrorBoundary>
    <div>
      <SharedDashboardMenuHeader :dashboard-title="dashboard.title" />
    </div>
    <DashboardComponent
      v-model:dashboard="sharedDashboard"
      :dashboard-key="dashboardKey"
      :base-filters="dashboardFilters.baseFilters"
      :widget-cores="dashboardWidgets.widgetCores"
      :updated-widget-render-keys="dashboardWidgets.updatedWidgetRenderKeys"
      :widget-titles="widget_titles"
      :is-editing="false"
    />
  </CmkErrorBoundary>
</template>
