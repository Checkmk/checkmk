<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CollapsibleContent from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import type { FilterConfigState } from '@/dashboard-wip/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard-wip/components/Wizard/types.ts'
import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import MultiFilter from './MultiFilter.vue'
import RestrictedToSingleFilter from './RestrictedToSingleFilter.vue'

interface Labels {
  title: TranslatedString
  tooltip: TranslatedString
}

interface Props {
  objectType: ObjectType
  objectSelectionMode: ElementSelection
  objectConfiguredFilters: FilterConfigState
  inFocus: boolean
  filterLabels: Labels
}

withDefaults(defineProps<Props>(), {
  filterLabels: () => ({
    title: 'Filter' as TranslatedString,
    tooltip: '' as TranslatedString
  })
})

const emit = defineEmits<{
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
}>()

const displayFilters = ref(true)

const onUpdateFilterValues = (filterId: string, values: ConfiguredValues | null) => {
  if (values === null) {
    throw new Error('Configured values cannot be null')
  }
  emit('update-filter-values', filterId, values)
}
</script>

<template>
  <CollapsibleTitle
    :title="filterLabels.title"
    :help_text="filterLabels.tooltip"
    :open="displayFilters"
    @toggle-open="displayFilters = !displayFilters"
  />
  <CollapsibleContent :open="displayFilters">
    <MultiFilter
      v-if="objectSelectionMode === ElementSelection.MULTIPLE"
      :object-type="objectType"
      :object-configured-filters="objectConfiguredFilters"
      :in-focus="inFocus"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="onUpdateFilterValues"
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
  </CollapsibleContent>
</template>
