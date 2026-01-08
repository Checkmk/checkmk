<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown'
import type { Suggestion } from '@/components/CmkSuggestions'

import { useDataSourcesCollection } from '@/dashboard/composables/api/useDataSourcesCollection'
import { useViewsCollection } from '@/dashboard/composables/api/useViewsCollection'

defineProps<{ readOnly: boolean }>()
const selectedView = defineModel<string | null>('selectedView', { required: true })

const { _t } = usei18n()
const {
  list: viewsList,
  ensureLoaded: ensureViewsLoaded,
  isLoading: viewsLoading,
  error: viewsError
} = useViewsCollection()
const {
  byId: dataSourcesById,
  ensureLoaded: ensureDataSourcesLoaded,
  isLoading: dataSourcesLoading,
  error: dataSourcesError
} = useDataSourcesCollection()

onMounted(async () => {
  await ensureViewsLoaded()
  await ensureDataSourcesLoaded()
})

const options = computed<Array<Suggestion>>(() =>
  (viewsList.value ?? [])
    .map((view) => ({
      name: view.id!,
      title: formatViewTitle(
        view.title!,
        view.id!,
        view.extensions.data_source!,
        view.extensions.is_mobile!
      )
    }))
    .sort((a, b) => a.title.localeCompare(b.title))
)

// Copied from cmk/gui/views/view_choices.py
// needs to be updated together until views have been migrated to vue.js
const formatViewTitle = (
  viewTitle: string,
  viewId: string,
  dataSource: string,
  isMobile: boolean
): TranslatedString => {
  const titleParts = []
  const dataSourceInfos = dataSourcesById.value[dataSource]?.extensions.infos ?? []

  if (isMobile) {
    titleParts.push(_t('Mobile'))
  }

  if (dataSourceInfos.includes('event')) {
    titleParts.push(_t('Event Console'))
  } else if (dataSource.startsWith('inv')) {
    titleParts.push(_t('HW/SW inventory'))
  } else if (dataSourceInfos.includes('aggr')) {
    titleParts.push(_t('BI'))
  } else if (dataSourceInfos.includes('log')) {
    titleParts.push(_t('Log'))
  } else if (dataSourceInfos.includes('service')) {
    titleParts.push(_t('Services'))
  } else if (dataSourceInfos.includes('host')) {
    titleParts.push(_t('Hosts'))
  } else if (dataSourceInfos.includes('hostgroup')) {
    titleParts.push(_t('Host groups'))
  } else if (dataSourceInfos.includes('servicegroup')) {
    titleParts.push(_t('Service groups'))
  }
  titleParts.push(`${viewTitle} (${viewId})`)

  return untranslated(titleParts.join(' - '))
}
</script>

<template>
  <div>
    <div v-if="viewsLoading || dataSourcesLoading" class="loading-indicator">
      {{ _t('Loading...') }}
    </div>

    <div v-if="viewsError || dataSourcesError" class="error-message">
      {{ viewsError ? _t('Error loading views: ') + viewsError : '' }}
      {{ dataSourcesError ? _t('Error loading data sources: ') + dataSourcesError : '' }}
    </div>

    <CmkDropdown
      v-if="!viewsLoading && !dataSourcesLoading && !viewsError && !dataSourcesError"
      v-model:selected-option="selectedView"
      :options="{ type: 'filtered', suggestions: options }"
      :label="_t('Select view')"
      :input-hint="_t('Choose from available views')"
      :disabled="readOnly"
      width="wide"
    />
  </div>
</template>
