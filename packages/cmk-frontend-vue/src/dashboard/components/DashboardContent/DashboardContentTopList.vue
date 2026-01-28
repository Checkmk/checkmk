<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, onBeforeMount, ref, watch } from 'vue'

import { cmkAjax } from '@/lib/ajax'
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkPerfometer from '@/components/CmkPerfometer.vue'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
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
      fetchingErrorMessage.value = (error as Error).message
    }
  }
}

onBeforeMount(() => {
  void fetchData()
})

watch(props, () => {
  void fetchData()
})

const headers: Ref<(string | TranslatedString)[]> = computed(() => {
  const _headers: (string | TranslatedString)[] = [_t('Host')]
  if (props.content.columns.show_service_description === true) {
    _headers.push(_t('Service'))
  }
  if (data.value !== undefined) {
    _headers.push(data.value.full_metric_name)
  }
  return _headers
})

const errorHeaders: string[] = [_t('Host'), _t('Service'), _t('Check command')]
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

const valueRange: Ref<[number, number] | undefined> = computed(() => {
  if (data.value) {
    return [data.value.value_range.min_value, data.value.value_range.max_value]
  }
  return undefined
})
</script>

<template>
  <DashboardContentContainer :effective-title="effectiveTitle" :general_settings="general_settings">
    <div v-if="fetchingErrorMessage" class="db-content-ntop__error error">
      {{ fetchingErrorMessage }}
    </div>
    <div v-else-if="data === undefined" class="db-content-top-list__loading">
      {{ _t('Loading Top list content') }}...
    </div>
    <div v-else>
      <table v-if="data!.entries.length" class="db-content-top-list__table">
        <tbody>
          <tr>
            <th v-for="(header, index) in headers" :key="index">{{ header }}</th>
          </tr>
          <tr v-for="(entry, index) in data!.entries" :key="index">
            <td>
              <a :href="hostViewUrl(entry)">
                {{ entry.host_name }}
              </a>
            </td>
            <td v-if="content.columns.show_service_description === true">
              <a :href="serviceViewUrl(entry)">
                {{ entry.service_description }}
              </a>
            </td>
            <td v-if="content.columns.show_bar_visualization === false">
              {{ entry.metric.formatted }}
            </td>
            <td v-else class="db-content-top-list__perfometer">
              <CmkPerfometer
                :value="entry.metric.value"
                :value-range="valueRange!"
                :formatted="entry.metric.formatted"
                :color="entry.metric.color"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="db-content-top-list__no-entries">
        {{ _t('No entries') }}
      </div>
      <CmkAlertBox v-if="data!.errors!.length" variant="error">
        <div class="db-content-top-list__error-msg">{{ errorMessage }}</div>
      </CmkAlertBox>
      <table v-if="data!.errors!.length" class="db-content-top-list__table">
        <tbody>
          <tr>
            <th v-for="(header, index) in errorHeaders" :key="index">{{ header }}</th>
          </tr>
          <tr v-for="(error, index) in data!.errors" :key="index">
            <td>
              <a :href="hostViewUrl(error)">
                {{ error.host_name }}
              </a>
            </td>
            <td>
              <a :href="serviceViewUrl(error)">
                {{ error.service_description }}
              </a>
            </td>
            <td>
              <a :href="checkCommandViewUrl(error)">
                {{ error.check_command }}
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-top-list__table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  empty-cells: show;

  tr {
    overflow: hidden;
    box-sizing: border-box;
    transition: all 0.15s ease-in;

    &:nth-child(even) {
      background-color: var(--even-tr-bg-color);
    }

    &:nth-child(odd) {
      background-color: var(--odd-tr-bg-color);
    }

    th {
      height: var(--dimension-8);
      padding: 0 var(--dimension-4);
      letter-spacing: 1px;
      text-align: left;
      vertical-align: middle;
      color: var(--font-color-dimmed);
      background-color: var(--odd-tr-bg-color);
    }

    td {
      height: 26px;
      padding: var(--dimension-2) var(--dimension-4);
      text-overflow: ellipsis;
      vertical-align: middle;

      a {
        text-decoration: none;

        &:hover {
          text-decoration: underline;
        }
      }
    }
  }
}

.db-content-top-list__perfometer {
  width: 150px;
}

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
