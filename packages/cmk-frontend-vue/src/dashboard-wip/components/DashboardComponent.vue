<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { useErrorBoundary } from '@/components/useErrorBoundary'

import type {
  ContentProps,
  ContentPropsRecord
} from '@/dashboard-wip/components/DashboardContent/types'
import RelativeGrid from '@/dashboard-wip/components/RelativeGrid/RelativeGrid.vue'
import ResponsiveGrid from '@/dashboard-wip/components/ResponsiveGrid/ResponsiveGrid.vue'
import type { DashboardFilters } from '@/dashboard-wip/composables/useDashboardFilters'
import type { DashboardWidgets } from '@/dashboard-wip/composables/useDashboardWidgets.ts'
import type {
  ContentRelativeGrid,
  ContentResponsiveGrid,
  DashboardConstants,
  DashboardModel
} from '@/dashboard-wip/types/dashboard'
import type { WidgetLayout } from '@/dashboard-wip/types/widget'

interface DashboardProps {
  constants: DashboardConstants
  dashboardName: string
  baseFilters: DashboardFilters['baseFilters']
  widgetCores: DashboardWidgets['widgetCores']
  isEditing: boolean
}

const props = defineProps<DashboardProps>()

const dashboard = defineModel<DashboardModel>('dashboard', { required: true })

defineEmits<{
  'widget:edit': [widgetId: string]
  'widget:delete': [widgetId: string]
  'widget:clone': [oldWidgetId: string, newLayout: WidgetLayout]
}>()

const widgetContentProps = computed<ContentPropsRecord>(() => {
  const record: Record<string, ContentProps> = {}
  for (const [widgetId, widget] of Object.entries(props.widgetCores.value)) {
    const widgetConstants = props.constants.widgets[widget.content.type]!
    if (!widgetConstants) {
      // TODO: until we have not migrated to the new format for dashboards
      // the old view widget will throw an error
      console.error(`Widget type ${widget.content.type} not found in constants`)
      continue
    }
    record[widgetId] = {
      widget_id: widgetId,
      general_settings: widget.general_settings,
      content: widget.content,
      effective_filter_context: {
        uses_infos: widget.filter_context.uses_infos,
        restricted_to_single: widgetConstants.filter_context.restricted_to_single,
        filters: {
          // TODO: might have to be adjusted where widget filter overwrites completely everything if available
          // to be discussed
          ...props.baseFilters.value,
          ...widget.filter_context.filters
        }
      },
      dashboardName: props.dashboardName
    }
  }
  return record
})

const { ErrorBoundary: errorBoundary } = useErrorBoundary()
</script>

<template>
  <errorBoundary>
    <ResponsiveGrid
      v-if="dashboard.content.layout.type === 'responsive_grid'"
      v-model:content="dashboard.content as ContentResponsiveGrid"
      :dashboard-name="props.dashboardName"
      :responsive-grid-breakpoints="props.constants.responsive_grid_breakpoints"
      :content-props="widgetContentProps"
      :is-editing="isEditing"
      @widget:edit="$emit('widget:edit', $event)"
      @widget:delete="$emit('widget:delete', $event)"
      @widget:clone="(oldWidgetId, newLayout) => $emit('widget:clone', oldWidgetId, newLayout)"
    />
    <RelativeGrid
      v-else-if="dashboard.content.layout.type === 'relative_grid'"
      v-model:content="dashboard.content as ContentRelativeGrid"
      :content-props="widgetContentProps"
      :is-editing="isEditing"
      :dashboard-constants="constants"
      @widget:edit="$emit('widget:edit', $event)"
    />
  </errorBoundary>
</template>
