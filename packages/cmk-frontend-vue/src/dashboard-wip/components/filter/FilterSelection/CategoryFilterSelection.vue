<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject } from 'vue'

import type { Filters } from '../composables/useFilters.ts'
import type { FilterDefinition } from '../types.ts'
import { parseFilterTypes } from '../utils.ts'
import FilterSelection from './FilterSelection.vue'
import { CATEGORY_DEFINITIONS } from './utils.ts'

interface Props {
  filters: Filters
  filterCategory: keyof typeof CATEGORY_DEFINITIONS
}

const props = defineProps<Props>()

const filterDefinitions = inject<Record<string, FilterDefinition> | null>('filterDefinitions', null)

if (!filterDefinitions) {
  throw new Error('Filter definitions are unavailable')
}

const filterCategories = parseFilterTypes(filterDefinitions, new Set([props.filterCategory]))

const categoryDefinition = computed(() => CATEGORY_DEFINITIONS[props.filterCategory])
</script>

<template>
  <FilterSelection
    :filters="filters"
    :category-filter="filterCategories.get(props.filterCategory)!"
    :category-definition="categoryDefinition!"
  />
</template>
