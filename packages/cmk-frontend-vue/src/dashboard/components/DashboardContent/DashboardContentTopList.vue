<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import { type AjaxResponseError, cmkAjax } from 'cmk-ui-library/lib/ajax'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onBeforeMount, ref, watch } from 'vue'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable'
import type { RankedTableColumn, RankedTableRow } from '@/dashboard/components/CmkRankedTable'
import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type {
  ComputedTopList,
  TopListContent,
  TopListEntry,
  TopListError
} from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

const { _t } = usei18n()
const props = defineProps<ContentProps<TopListContent>>()
const cmkToken = useInjectCmkToken()
const isPublicDashboard = useInjectIsPublicDashboard()
const data = ref<ComputedTopList | undefined>(undefined)
const fetchingErrorMessage = ref<string | null>(null)

const fetchData = async () => {
  if (cmkToken === undefined) {
    const response = await dashboardAPI.computeTopListData(
      props.content,
      props.effective_filter_context.filters
    )
    data.value = response.value
  } else {
    try {
      const httpVarsString: string = new URLSearchParams({
        widget_id: props.widget_id,
        'cmk-token': cmkToken
      }).toString()
      data.value = await cmkAjax(`compute_top_list_data_token_auth.py?${httpVarsString}`, {})
    } catch (error) {
      console.error('Error initializing top list content:', error)
      fetchingErrorMessage.value = `${_t('Failed to fetch top list data:')} ${(error as AjaxResponseError).response?.result ?? (error as Error).message}`
    }
  }
}

onBeforeMount(() => {
  void fetchData()
})

const dataParameters = computed(() =>
  JSON.stringify({ filters: props.effective_filter_context.filters, content: props.content })
)

watch(dataParameters, () => {
  void fetchData()
})

const errorMessage: string = _t(
  `Due to a limitation in how Checkmk handles metrics internally, the results contain conflicting metrics and this top list may be incorrect or incomplete.\n
    This is caused by the service check commands with an example host and service in the following table.\n
    You can use these examples to identify hosts and services that must be filtered out in the top list configuration to resolve the problem.`
)

const hostViewUrl = (entry: TopListEntry | TopListError) => {
  const urlParams = new URLSearchParams({
    view_name: 'host',
    site: entry.site_id,
    host: entry.host_name
  }).toString()
  return `view.py?${urlParams}`
}

const serviceViewUrl = (entry: TopListEntry | TopListError) => {
  const urlParams = new URLSearchParams({
    view_name: 'service',
    site: entry.site_id,
    host: entry.host_name,
    service: entry.service_description
  }).toString()
  return `view.py?${urlParams}`
}

const checkCommandViewUrl = (error: TopListError) => {
  const urlParams = new URLSearchParams({
    view_name: 'searchsvc',
    filled_in: 'filter',
    _active: 'check_command',
    check_command: error.check_command
  }).toString()
  return `view.py?${urlParams}`
}

// Links to the monitoring views are suppressed on public dashboards, where the
// recipient has no session to follow them with.
function link(url: string): { href?: string } {
  return isPublicDashboard ? {} : { href: url }
}

const columns = computed<RankedTableColumn[]>(() => {
  const showBar = props.content.columns.show_bar_visualization !== false
  const result: RankedTableColumn[] = [
    { key: 'host', title: _t('Host'), render: 'text', bar: false }
  ]
  if (props.content.columns.show_service_description === true) {
    result.push({ key: 'service', title: _t('Service'), render: 'text', bar: false })
  }
  result.push({
    key: 'value',
    title: data.value?.full_metric_name ?? '',
    render: 'count',
    bar: showBar,
    // The backend derives the range from the widget's "display range" setting.
    ...(showBar && data.value !== undefined
      ? {
          barRange: [data.value.value_range.min_value, data.value.value_range.max_value] as [
            number,
            number
          ]
        }
      : {})
  })
  return result
})

// The backend delivers the entries pre-ranked, pre-formatted and colored by metric.
const rows = computed<RankedTableRow[]>(() =>
  (data.value?.entries ?? []).map((entry) => ({
    host: { value: entry.host_name, ...link(hostViewUrl(entry)) },
    service: { value: entry.service_description, ...link(serviceViewUrl(entry)) },
    value: {
      value: entry.metric.value,
      formatted: entry.metric.formatted,
      color: entry.metric.color
    }
  }))
)

const errorColumns: RankedTableColumn[] = [
  { key: 'host', title: _t('Host'), render: 'text', bar: false },
  { key: 'service', title: _t('Service'), render: 'text', bar: false },
  { key: 'checkCommand', title: _t('Check command'), render: 'text', bar: false }
]

const errorRows = computed<RankedTableRow[]>(() =>
  (data.value?.errors ?? []).map((error) => ({
    host: { value: error.host_name, ...link(hostViewUrl(error)) },
    service: { value: error.service_description, ...link(serviceViewUrl(error)) },
    checkCommand: { value: error.check_command, ...link(checkCommandViewUrl(error)) }
  }))
)
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :is-scrollable-preview="isPreview ?? false"
  >
    <div v-if="fetchingErrorMessage" class="db-content-top-list__error error">
      {{ fetchingErrorMessage }}
    </div>
    <div v-else-if="data === undefined" class="db-content-top-list__loading">
      {{ _t('Loading Top list content') }}...
    </div>
    <div v-else>
      <CmkRankedTable v-if="rows.length" :columns="columns" :rows="rows" />
      <div v-else class="db-content-top-list__no-entries">
        {{ _t('No entries') }}
      </div>
      <template v-if="errorRows.length">
        <CmkAlertBox variant="error">
          <div class="db-content-top-list__error-msg">{{ errorMessage }}</div>
        </CmkAlertBox>
        <CmkRankedTable :columns="errorColumns" :rows="errorRows" />
      </template>
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-top-list__no-entries {
  padding: var(--spacing);
}

.db-content-top-list__loading {
  padding: var(--dimension-6);
  text-align: center;
}

.db-content-top-list__error-msg {
  white-space: pre-line;
  line-height: var(--font-size-normal);
}
</style>
