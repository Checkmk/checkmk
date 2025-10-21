<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown'
import type { Suggestion } from '@/components/CmkSuggestions'

const { _t } = usei18n()

export interface SidebarElementApiResult {
  id: string
  title: string
}

export interface SidebarElement {
  id: string
  title: TranslatedString
}

const selectedSidebarElement = defineModel<string | null>('selectedSidebarElement', {
  required: true
})
const apiSidebarElements = ref<SidebarElement[]>([])
const isLoading = ref(true)
const hasError = ref<string | null>(null)

async function loadSidebarElements() {
  const API_ROOT = 'api/unstable'
  const url = `${API_ROOT}/domain-types/sidebar_element/collections/all`

  try {
    const response = await fetchRestAPI(url, 'GET')
    await response.raiseForStatus()
    const data = await response.json()

    apiSidebarElements.value = (data.value as SidebarElementApiResult[]).map((item) => ({
      id: item.id,
      title: untranslated(item.title)
    }))
    hasError.value = null
  } catch (error) {
    console.error('Failed to fetch sidebar elements: ', error)
    hasError.value = _t('Failed to load sidebar elements.')
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  await loadSidebarElements()
})

const dropdownOptions = computed<Suggestion[]>(() =>
  apiSidebarElements.value.map((el) => ({
    name: el.id,
    title: el.title
  }))
)
</script>

<template>
  <div v-if="isLoading" class="loading-indicator">
    {{ _t('Loading sidebar elements...') }}
  </div>
  <div v-if="hasError" class="error-message">
    {{ hasError }}
  </div>
  <CmkDropdown
    v-if="!isLoading && !hasError"
    v-model:selected-option="selectedSidebarElement"
    :options="{ type: 'fixed', suggestions: dropdownOptions }"
    :label="_t('Sidebar element')"
  />
</template>
