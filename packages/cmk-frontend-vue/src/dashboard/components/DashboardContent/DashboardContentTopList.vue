<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable'
import type { RankedTableColumn, RankedTableRow } from '@/dashboard/components/CmkRankedTable'
import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type {
  ComputedTopList,
  TopListContent,
  TopListEntry,
  TopListError
} from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'

import WidgetFigureFrame from './figures/WidgetFigureFrame.vue'
import type { ContentProps } from './types.ts'

const { _t } = usei18n()
const props = defineProps<ContentProps<TopListContent>>()
const isPublicDashboard = useInjectIsPublicDashboard()
const { source, headers } = useWidgetSource(props)
const { state, retry } = useWidgetData(
  () => dashboardAPI.computeTopList({ source: source.value }, headers),
  () => [props.content, props.effective_filter_context],
  () => props.tick
)

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

// Only the ranked rows follow the contextual link; the error table's links help to fix the
// configuration.
function contextualLink(url: string): { href?: string } {
  return props.content.contextual_link.type === 'none' ? {} : link(url)
}

function columns(topList: ComputedTopList): RankedTableColumn[] {
  const showBar = props.content.columns.show_bar_visualization !== false
  const result: RankedTableColumn[] = [
    { key: 'host', title: _t('Host'), render: 'text', bar: false }
  ]
  if (props.content.columns.show_service_description === true) {
    result.push({ key: 'service', title: _t('Service'), render: 'text', bar: false })
  }
  const value: RankedTableColumn = {
    key: 'value',
    title: topList.full_metric_name,
    render: 'count',
    bar: showBar
  }
  if (showBar) {
    // The backend derives the range from the widget's "display range" setting.
    value.barRange = [topList.value_range.min_value, topList.value_range.max_value]
  }
  result.push(value)
  return result
}

// The backend delivers the entries pre-ranked, pre-formatted and colored by metric.
function rows(topList: ComputedTopList): RankedTableRow[] {
  return topList.entries.map((entry) => ({
    host: { value: entry.host_name, ...contextualLink(hostViewUrl(entry)) },
    service: { value: entry.service_description, ...contextualLink(serviceViewUrl(entry)) },
    value: {
      value: entry.metric.value,
      formatted: entry.metric.formatted,
      color: entry.metric.color
    }
  }))
}

const errorColumns: RankedTableColumn[] = [
  { key: 'host', title: _t('Host'), render: 'text', bar: false },
  { key: 'service', title: _t('Service'), render: 'text', bar: false },
  { key: 'checkCommand', title: _t('Check command'), render: 'text', bar: false }
]

function errorRows(topList: ComputedTopList): RankedTableRow[] {
  return topList.errors.map((error) => ({
    host: { value: error.host_name, ...link(hostViewUrl(error)) },
    service: { value: error.service_description, ...link(serviceViewUrl(error)) },
    checkCommand: { value: error.check_command, ...link(checkCommandViewUrl(error)) }
  }))
}
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value }">
      <div class="db-content-top-list__scroll">
        <div :class="{ 'db-content-top-list__preview-shield': isPreview }">
          <CmkRankedTable
            v-if="value.entries.length"
            :columns="columns(value)"
            :rows="rows(value)"
          />
          <div v-else class="db-content-top-list__no-entries">
            {{ _t('No entries') }}
          </div>
          <template v-if="value.errors.length">
            <CmkAlertBoxDeprecated variant="error">
              <div class="db-content-top-list__error-msg">{{ errorMessage }}</div>
            </CmkAlertBoxDeprecated>
            <CmkRankedTable :columns="errorColumns" :rows="errorRows(value)" />
          </template>
        </div>
      </div>
    </template>
  </WidgetFigureFrame>
</template>

<style scoped>
.db-content-top-list__scroll {
  height: 100%;
  overflow: auto;
}

.db-content-top-list__preview-shield {
  pointer-events: none;
}

.db-content-top-list__no-entries {
  padding: var(--spacing);
}

.db-content-top-list__error-msg {
  white-space: pre-line;
  line-height: var(--font-size-normal);
}
</style>
