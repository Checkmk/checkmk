<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable'
import type { RankedTableColumn, RankedTableRow } from '@/dashboard/components/CmkRankedTable'
import { useComputedWidget } from '@/dashboard/composables/useComputedWidget'
import { useInjectDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import { type ContextualLinkEntry, contextualLinkEntries } from '@/dashboard/lib/contextualLinkUrl'
import type {
  ComputedTopList,
  LinkProperties,
  TopListContent,
  TopListEntry,
  TopListError
} from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import { useTimeRangeVariables } from '@/graphing/GlobalTimePicker/timeRangeUrl'
import { hostServicesPageUrl } from '@/monitoring/shared/hostServicesPageUrl'
import { DRILLED_FROM_PARAM } from '@/page-header/drillUp'

import type { ContentProps } from '../types.ts'
import WidgetDataErrorAlert from './WidgetDataErrorAlert.vue'
import WidgetFigureFrame from './WidgetFigureFrame.vue'

const { _t } = usei18n()
const props = defineProps<ContentProps<TopListContent>>()
const isPublicDashboard = useInjectIsPublicDashboard()
const drillDownSource = useInjectDrillDownSource()
const timeRange = useTimeRangeVariables()
// A refresh animates from the rows on display, a changed configuration or filter starts afresh:
// each top list is drawn with the configuration it was fetched for, and keys its table by it.
interface FetchedFor {
  key: string
  content: TopListContent
}
const fetchedFor = new WeakMap<ComputedTopList, FetchedFor>()
const { state, retry, fetching, lastSuccessAt } = useComputedWidget(
  props,
  async (body, headers) => {
    const input = {
      key: JSON.stringify([props.content, props.effective_filter_context]),
      content: props.content
    }
    const response = await dashboardAPI.computeTopList(body, headers)
    fetchedFor.set(response.value, input)
    return response
  }
)

function contentOf(topList: ComputedTopList): TopListContent {
  return fetchedFor.get(topList)?.content ?? props.content
}

const errorMessage: string = _t(
  `Due to a limitation in how Checkmk handles metrics internally, the results contain conflicting metrics and this top list may be incorrect or incomplete.\n
    This is caused by the service check commands with an example host and service in the following table.\n
    You can use these examples to identify hosts and services that must be filtered out in the top list configuration to resolve the problem.`
)

const hostServicesUrl = (entry: TopListEntry | TopListError) =>
  hostServicesPageUrl({ name: entry.host_name, site_id: entry.site_id })

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

// A ranked row's built-in link is a drill-down too, so it names the dashboard it leaves.
function drilledFromUrl(url: string): string {
  const title = drillDownSource.value
  if (!title) {
    return url
  }
  const target = new URL(url, window.location.href)
  target.searchParams.set(DRILLED_FROM_PARAM, title)
  return target.href
}

// Only the ranked rows follow the contextual link; the error table's links help to fix the
// configuration. The server resolves no built-in link, as each cell has its own view.
function contextualLink(
  topList: ComputedTopList,
  builtInUrl: string,
  properties: LinkProperties
): { href?: string } | { choices: ContextualLinkEntry[] } {
  if (props.content.contextual_link.type === 'default') {
    return link(drilledFromUrl(builtInUrl))
  }
  const entries = contextualLinkEntries(
    topList.links,
    properties,
    props.effective_filter_context.filters,
    timeRange.value,
    drillDownSource.value
  )
  if (entries.length === 0 || isPublicDashboard) {
    return {}
  }
  return entries.length === 1 ? { href: entries[0]!.href } : { choices: entries }
}

function showRank(content: TopListContent): boolean {
  return content.columns.show_rank_numbers !== false
}

// Without a top list yet, the value column has no title and no range.
function columns(content: TopListContent, topList?: ComputedTopList): RankedTableColumn[] {
  const showBar = content.columns.show_bar_visualization !== false
  const result: RankedTableColumn[] = [
    { key: 'host', title: _t('Host'), render: 'text', bar: false }
  ]
  if (content.columns.show_service_description === true) {
    result.push({
      key: 'service',
      title: _t('Service'),
      render: 'text',
      bar: false,
      tone: 'secondary'
    })
  }
  const value: RankedTableColumn = {
    key: 'value',
    title: topList?.full_metric_name ?? '',
    render: 'count',
    bar: showBar
  }
  // A fixed display range scales the bars; without one, they grow from zero by their size.
  if (showBar && topList && content.display_range !== 'automatic') {
    value.barRange = [topList.value_range.min_value, topList.value_range.max_value]
  }
  result.push(value)
  return result
}

// The backend delivers the entries pre-ranked, pre-formatted and colored by metric.
function rows(topList: ComputedTopList): RankedTableRow[] {
  return topList.entries.map((entry) => ({
    [ENTRY_KEY]: JSON.stringify([entry.site_id, entry.host_name, entry.service_description]),
    host: {
      value: entry.host_name,
      ...contextualLink(topList, hostServicesUrl(entry), entry.host_link_properties)
    },
    service: {
      value: entry.service_description,
      ...contextualLink(topList, serviceViewUrl(entry), entry.service_link_properties)
    },
    value: {
      value: entry.metric.value,
      formatted: entry.metric.value_text,
      unit: entry.metric.unit ?? undefined,
      color: entry.metric.color
    }
  }))
}

// Rows carry their entry's identity in a cell no column shows.
const ENTRY_KEY = 'entry'

function entryKey(row: RankedTableRow): string {
  return String(row[ENTRY_KEY])
}

const errorColumns: RankedTableColumn[] = [
  { key: 'host', title: _t('Host'), render: 'text', bar: false },
  { key: 'service', title: _t('Service'), render: 'text', bar: false, tone: 'secondary' },
  { key: 'checkCommand', title: _t('Check command'), render: 'text', bar: false }
]

function errorRows(topList: ComputedTopList): RankedTableRow[] {
  return topList.errors.map((error) => ({
    host: { value: error.host_name, ...link(hostServicesUrl(error)) },
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
    <template #loading>
      <div class="db-content-top-list__scroll">
        <div class="db-content-top-list__fill">
          <CmkRankedTable
            :columns="columns(content)"
            :rows="[]"
            :placeholder="{ kind: 'loading', rows: content.limit_to }"
            :show-rank="showRank(content)"
            :label="effectiveTitle"
          />
        </div>
      </div>
    </template>
    <template #error="{ detail, retry: retryFetch }">
      <WidgetDataErrorAlert :detail="detail" :last-success-at="lastSuccessAt" @retry="retryFetch" />
    </template>
    <template #default="{ value }">
      <div class="db-content-top-list__scroll">
        <div
          :class="{
            'db-content-top-list__preview-shield': isPreview,
            'db-content-top-list__fill': !value.errors.length
          }"
        >
          <CmkRankedTable
            v-if="value.entries.length"
            :key="fetchedFor.get(value)?.key ?? ''"
            :columns="columns(contentOf(value), value)"
            :rows="rows(value)"
            :row-key="entryKey"
            :busy="fetching"
            :show-rank="showRank(contentOf(value))"
            :label="effectiveTitle"
          />
          <CmkRankedTable
            v-else
            :columns="columns(contentOf(value), value)"
            :rows="[]"
            :placeholder="{ kind: 'empty', rows: content.limit_to }"
            :show-rank="showRank(contentOf(value))"
          >
            <template #empty>
              <CmkHeading type="h4">{{ _t('No data') }}</CmkHeading>
              <CmkParagraph>
                {{ _t('Nothing matches the widget filter in the selected time frame.') }}
              </CmkParagraph>
            </template>
          </CmkRankedTable>
          <template v-if="value.errors.length">
            <CmkAlertBoxDeprecated variant="error">
              <div class="db-content-top-list__error-msg">{{ errorMessage }}</div>
            </CmkAlertBoxDeprecated>
            <CmkRankedTable
              :columns="errorColumns"
              :rows="errorRows(value)"
              :label="_t('Services with conflicting metrics')"
            />
          </template>
        </div>
      </div>
    </template>
  </WidgetFigureFrame>
</template>

<style scoped>
/* Without errors the table fills the box and scrolls itself, under its sticky header. */
.db-content-top-list__scroll {
  box-sizing: border-box;
  height: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  overflow: auto;
}

.db-content-top-list__preview-shield {
  pointer-events: none;
}

.db-content-top-list__fill {
  height: 100%;
}

.db-content-top-list__error-msg {
  white-space: pre-line;
  line-height: var(--font-size-normal);
}
</style>
