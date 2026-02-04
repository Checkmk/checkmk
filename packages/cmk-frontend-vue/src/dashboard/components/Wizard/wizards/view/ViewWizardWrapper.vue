<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'

import CmkIcon from '@/components/CmkIcon'

import ViewWizardInner from '@/dashboard/components/Wizard/wizards/view/ViewWizardInner.vue'
import { useDataSourcesCollection } from '@/dashboard/composables/api/useDataSourcesCollection'
import { useProvideViews } from '@/dashboard/composables/useProvideViews'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

const { byId: viewsById, ready: viewsReady } = useProvideViews()
const { byId: datasourcesById, ensureLoaded: ensureDataSourcesLoaded } = useDataSourcesCollection()

const dataSourcesReady = ref(false)
onMounted(async () => {
  await ensureDataSourcesLoaded()
  dataSourcesReady.value = true
})

interface ViewWizardProps {
  dashboardKey: DashboardKey
  contextFilters: ContextFilters
  editWidgetSpec?: WidgetSpec | null
  editWidgetId?: string | null
}

const { editWidgetSpec = null, editWidgetId = null } = defineProps<ViewWizardProps>()

defineEmits<{
  goBack: []
  close: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()
</script>

<template>
  <template v-if="viewsReady && dataSourcesReady">
    <ViewWizardInner
      :dashboard-key="dashboardKey"
      :views-by-id="viewsById"
      :context-filters="contextFilters"
      :edit-widget-spec="editWidgetSpec"
      :edit-widget-id="editWidgetId"
      :datasources-by-id="datasourcesById"
      @go-back="$emit('goBack')"
      @close="$emit('close')"
      @add-widget="
        (content, generalSettings, filterContext) =>
          $emit('addWidget', content, generalSettings, filterContext)
      "
    />
  </template>
  <template v-else>
    <CmkIcon name="load-graph" size="xxlarge" />
  </template>
</template>
