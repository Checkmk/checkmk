<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import CatalogPanelHeader from '@/dashboard/components/Wizard/components/collapsible/CatalogPanelHeader.vue'
import type { FilterConfigState } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard/components/Wizard/types.ts'
import type { ConfiguredValues } from '@/dashboard/components/filter/types.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

import MultiFilter from './MultiFilter.vue'
import RestrictedToSingleFilter from './RestrictedToSingleFilter.vue'

interface Labels {
  title: TranslatedString
  tooltip: TranslatedString
}

defineProps<{
  objectType: ObjectType
  objectSelectionMode: ElementSelection
  objectConfiguredFilters: FilterConfigState
  inFocus: boolean
  filterLabels: Labels
}>()

const emit = defineEmits<{
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'remove-filter', filterId: string): void
}>()

const onUpdateFilterValues = (filterId: string, values: ConfiguredValues | null) => {
  if (values === null) {
    throw new Error('Configured values cannot be null')
  }
  emit('update-filter-values', filterId, values)
}
</script>

<template>
  <CmkCatalogPanel :title="filterLabels.title">
    <template #header>
      <CatalogPanelHeader :title="filterLabels.title" :help-text="filterLabels.tooltip" />
    </template>
    <MultiFilter
      v-if="objectSelectionMode === ElementSelection.MULTIPLE"
      :object-type="objectType"
      :object-configured-filters="objectConfiguredFilters"
      :in-focus="inFocus"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="onUpdateFilterValues"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
    <RestrictedToSingleFilter
      v-else
      :configured-filter-values="objectConfiguredFilters[objectType] || null"
      :object-type="objectType"
      @update:configured-filter-values="
        (values) => {
          onUpdateFilterValues(objectType, values)
        }
      "
    />
  </CmkCatalogPanel>
</template>
