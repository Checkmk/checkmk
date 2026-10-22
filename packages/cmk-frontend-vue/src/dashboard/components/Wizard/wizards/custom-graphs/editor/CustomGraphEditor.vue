<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import { useFilterDefinitions } from 'cmk-ui-library/components/filter'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, useTemplateRef } from 'vue'

import { type CustomGraphOptions, getDesignerConfig } from '@/graphing/designer/api'
import DesignerBody from '@/graphing/designer/components/DesignerBody.vue'
import { useBlockingIssues } from '@/graphing/designer/composables/useBlockingIssues'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { fromApiDataSource, toApiDataSources } from '@/graphing/designer/drafts'
import type { ApiDataSourceInput, GraphItem } from '@/graphing/designer/types'
import { isValid } from '@/graphing/designer/validation'
import type { RequestedTimeRange } from '@/graphing/types'

import type { EmbeddedGraphDefinition } from './types'

const {
  title,
  timeRange,
  dataSources = []
} = defineProps<{
  title: string
  timeRange: RequestedTimeRange
  /** The sources the editor starts from, read once; re-key the editor to start over. */
  dataSources?: readonly ApiDataSourceInput[]
}>()

const graphOptions = defineModel<CustomGraphOptions>('graphOptions', { required: true })

const { _tn } = usei18n()

const filterDefinitions = useFilterDefinitions()

// Expose before the await: the parent's template ref is set when this component's setup
// suspends, not when it finishes, and it keeps whatever was exposed at that moment.
defineExpose({ submit })

const designerBody = useTemplateRef('designerBody')

let loadError: string | null = null
const config = await getDesignerConfig().catch((error: unknown) => {
  loadError = error instanceof Error ? error.message : String(error)
  return null
})

const store = useGraphItems(config?.palette ?? [])
store.replaceAll(dataSources.map(fromApiDataSource))

const { blockingIssues, issuesByRow, blockedIds, hasAttemptedSave } = useBlockingIssues(
  store.items,
  () => filterDefinitions
)

// Above the tabs, so it stays in view while the calculation form covers the metrics table.
const blockedSummary = computed(() =>
  _tn(
    'Fix the issues with ID %{ids} before you continue.',
    'Fix the issues with IDs %{ids} before you continue.',
    blockedIds.value.length,
    { ids: blockedIds.value.join(', ') }
  )
)

/** The definition to store, or null while a source has issues, which then show at their rows. */
function submit(): EmbeddedGraphDefinition | null {
  hasAttemptedSave.value = true
  if (blockingIssues.value.length > 0) {
    // The issues show in the metrics table, which an open calculation form covers.
    designerBody.value?.closeCalculation()
    return null
  }
  const items = store.items.value.filter((item): item is GraphItem =>
    isValid(item, filterDefinitions)
  )
  return { data_sources: toApiDataSources(items), graph_options: graphOptions.value }
}
</script>

<template>
  <CmkAlert v-if="config === null" variant="error" :text="untranslated(loadError ?? '')" />
  <DesignerBody
    v-else
    ref="designerBody"
    :store="store"
    :graph-options="graphOptions"
    :title="title"
    graph-name=""
    mode="edit"
    calculation-placement="inline"
    :thresholds="{ warning: config.warning_color, critical: config.critical_color }"
    :telemetry-metrics-available="config.telemetry_metrics_available"
    :create-services-available="config.create_services_available"
    :telemetry-metrics-default-title="config.telemetry_metrics_default_title"
    :title-macros="config.title_macros"
    :issues-by-row="issuesByRow"
    :time-range="timeRange"
    @update-graph-options="(options) => (graphOptions = options)"
  >
    <template #alerts>
      <CmkAlert
        v-if="hasAttemptedSave && blockingIssues.length > 0"
        variant="error"
        :text="blockedSummary"
      />
    </template>
  </DesignerBody>
</template>
