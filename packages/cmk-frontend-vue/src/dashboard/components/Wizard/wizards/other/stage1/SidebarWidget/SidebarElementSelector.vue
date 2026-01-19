<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import type { Suggestion } from '@/components/CmkSuggestions'

import type { SidebarElementEntry } from './composables/useSidebarElements'

const { _t } = usei18n()

interface Props {
  elements: readonly SidebarElementEntry[]
  hasError: boolean
  isLoading: boolean
}
const props = defineProps<Props>()

const selectedSidebarElement = defineModel<string>('selectedSidebarElement', {
  required: true
})

const dropdownOptions = computed<Suggestion[]>(() =>
  props.elements.map((el) => ({
    name: el.id,
    title: el.title
  }))
)
</script>

<template>
  <div v-if="isLoading" class="loading-indicator">
    {{ _t('Loading sidebar elements...') }}
  </div>
  <div v-else-if="hasError" class="error-message">
    {{ _t('Failed to load sidebar elements.') }}
  </div>
  <template v-else>
    <CmkDropdown
      v-model:selected-option="selectedSidebarElement"
      :options="{ type: 'filtered', suggestions: dropdownOptions }"
      :label="_t('Select option')"
      width="fill"
    />
  </template>
</template>
