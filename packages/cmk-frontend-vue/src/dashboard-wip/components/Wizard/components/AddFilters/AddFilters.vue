<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import FilterSelection from '@/dashboard-wip/components/filter/FilterSelection/FilterSelection.vue'
import { CATEGORY_DEFINITIONS } from '@/dashboard-wip/components/filter/FilterSelection/utils'
import { type Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import { parseFilterTypes, useFilterDefinitions } from '@/dashboard-wip/components/filter/utils'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import ContentSpacer from '../ContentSpacer.vue'
import StepsHeader from '../StepsHeader.vue'

const { _t } = usei18n()

interface AddFiltersProps {
  filterSelectionTarget: ObjectType
  close: () => void
}
const props = defineProps<AddFiltersProps>()

const filters = defineModel<Filters>('filters', { required: true })

const filterDefinitions = useFilterDefinitions()

const filterCategory = computed(() => {
  const categories = parseFilterTypes(
    filterDefinitions,
    new Set([props.filterSelectionTarget as unknown as string])
  )
  return categories.get(props.filterSelectionTarget)
})
</script>

<template>
  <StepsHeader :title="_t('Add filter')" @back="props.close" />
  <ContentSpacer />

  <FilterSelection
    :key="`${filterSelectionTarget}`"
    :category-filter="filterCategory || []"
    :category-definition="CATEGORY_DEFINITIONS.host!"
    :filters="filters"
    class="filter-selection__item"
  />
</template>
