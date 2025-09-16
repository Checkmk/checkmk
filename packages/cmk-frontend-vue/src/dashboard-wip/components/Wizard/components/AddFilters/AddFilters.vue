<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import FilterSelection from '@/dashboard-wip/components/filter/FilterSelection/FilterSelection.vue'
import { CATEGORY_DEFINITIONS } from '@/dashboard-wip/components/filter/FilterSelection/utils'
import { type Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import { parseFilterTypes, useFilterDefinitions } from '@/dashboard-wip/components/filter/utils'

import ContentSpacer from '../ContentSpacer.vue'
import StepsHeader from '../StepsHeader.vue'
import { type UseAddFilter } from './composables/useAddFilters'

const { _t } = usei18n()

interface AddFiltersProps {
  handler: UseAddFilter
}
const props = defineProps<AddFiltersProps>()

const filters = defineModel<Filters>('filters', { required: true })

const filterDefinitions = useFilterDefinitions()

const selectedCategory = props.handler.target.value
const filterCategories = parseFilterTypes(
  filterDefinitions,
  new Set([selectedCategory as unknown as string])
)
</script>

<template>
  <StepsHeader :title="_t('Add filter')" @back="props.handler.close" />
  <ContentSpacer />

  <FilterSelection
    :category-filter="filterCategories.get(selectedCategory) || []"
    :category-definition="CATEGORY_DEFINITIONS.host!"
    :filters="filters"
    class="filter-selection__item"
  />
</template>
