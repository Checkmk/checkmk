<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { ButtonVariants } from 'cmk-ui-library/components/CmkDropdown/CmkDropdownButton.vue'
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, onMounted, ref } from 'vue'

import { useDataSourcesCollection } from '@/dashboard/composables/api/useDataSourcesCollection'
import { useViewsCollection } from '@/dashboard/composables/api/useViewsCollection'

import { withStoredName } from './storedName'

type Width = ButtonVariants['width']

const { readOnly, width = 'wide' } = defineProps<{
  readOnly: boolean
  width?: Width
}>()
const selectedView = defineModel<string | null>('selectedView', { required: true })

const { _t } = usei18n()
const { list: viewsList, ensureLoaded: ensureViewsLoaded, error: viewsError } = useViewsCollection()
const {
  byId: dataSourcesById,
  ensureLoaded: ensureDataSourcesLoaded,
  error: dataSourcesError
} = useDataSourcesCollection()

// The dropdown waits for both loads, so it does not flash up empty before or between them.
const loaded = ref(false)

onMounted(async () => {
  await ensureViewsLoaded()
  await ensureDataSourcesLoaded()
  loaded.value = true
})

const options = computed<Array<Suggestion>>(() =>
  withStoredName(
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
      .sort((a: Suggestion, b: Suggestion) => a.title.localeCompare(b.title)),
    selectedView.value
  )
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
    <div v-if="!loaded" class="loading-indicator">
      {{ _t('Loading...') }}
    </div>

    <div v-if="viewsError || dataSourcesError" class="error-message">
      {{ viewsError ? _t('Error loading views: ') + viewsError : '' }}
      {{ dataSourcesError ? _t('Error loading data sources: ') + dataSourcesError : '' }}
    </div>

    <CmkDropdown
      v-if="loaded && !viewsError && !dataSourcesError"
      v-model="selectedView"
      :options="{ type: 'filtered', suggestions: options }"
      :label="_t('Select view')"
      :input-hint="_t('Choose from available views')"
      :disabled="readOnly"
      :width="width"
    />
  </div>
</template>
