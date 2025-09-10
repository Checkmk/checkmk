<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { ContentProps } from '@/dashboard-wip/components/DashboardContent/types'
import type { DashboardFilters } from '@/dashboard-wip/composables/useDashboardFilters'
import type { DashboardWidgets } from '@/dashboard-wip/composables/useDashboardWidgets.ts'
import type { DashboardConstants, DashboardModel } from '@/dashboard-wip/types/dashboard'

interface DashboardProps {
  dashboardName: string
  dashboardOwner: string
  baseFilters: DashboardFilters['baseFilters']
  widgetCores: DashboardWidgets['widgetCores']
  constants: DashboardConstants
  isEditing: boolean
}

const props = defineProps<DashboardProps>()

const dashboard = defineModel<DashboardModel>('dashboard', { required: true })

const widgetContentProps = computed(() => {
  const record: Record<string, ContentProps> = {}
  for (const [widgetId, widget] of Object.entries(props.widgetCores.value)) {
    const widgetConstants = props.constants.widgets[widget.content.type]!
    record[widgetId] = {
      widget_id: widgetId,
      general_settings: widget.general_settings,
      content: widget.content,
      effective_filter_context: {
        uses_infos: widget.filter_context.uses_infos,
        restricted_to_single: widgetConstants.filter_context.restricted_to_single,
        // @ts-expect-error TODO: filters should be adapted to be <string, string> only
        filters: {
          // TODO: might have to be adjusted where widget filter overwrites completely everything if available
          // to be discussed
          ...props.baseFilters.value,
          ...widget.filter_context.filters
        }
      },
      dashboardName: props.dashboardName,
      dashboardOwner: props.dashboardOwner
    }
  }
  return record
})

console.log('Remove this log', widgetContentProps, dashboard)
</script>

<template>
  <div></div>
</template>
