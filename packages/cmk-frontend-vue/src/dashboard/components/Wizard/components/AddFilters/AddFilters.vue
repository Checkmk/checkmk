<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import FilterSelection from '@/dashboard/components/filter/FilterSelection/FilterSelection.vue'
import { CATEGORY_DEFINITIONS } from '@/dashboard/components/filter/FilterSelection/utils'
import { type Filters } from '@/dashboard/components/filter/composables/useFilters'
import { parseFilterTypes, useFilterDefinitions } from '@/dashboard/components/filter/utils'
import type { ObjectType } from '@/dashboard/types/shared.ts'

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
  <div class="db-add-filters__container">
    <StepsHeader :title="_t('Add filter')" @back="props.close" />
    <ContentSpacer :height="40" />

    <FilterSelection
      :key="`${filterSelectionTarget}`"
      :category-filter="filterCategory || []"
      :category-definition="
        (filterSelectionTarget === 'service'
          ? CATEGORY_DEFINITIONS.service
          : CATEGORY_DEFINITIONS.host)!
      "
      :filters="filters"
      class="db-add-filters__selection"
    />
  </div>
</template>

<style scoped>
.db-add-filters__container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.db-add-filters__selection {
  min-height: 0;
  flex-grow: 1;

  /* We want the same padding on both sides and the bottom, however the parent already sets some. */
  padding: 0 var(--dimension-7) calc(var(--dimension-7) - var(--spacing))
    calc(var(--dimension-7) - var(--spacing));
}
</style>
