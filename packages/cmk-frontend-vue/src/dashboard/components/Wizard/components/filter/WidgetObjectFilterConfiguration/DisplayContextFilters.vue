<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkLabel from '@/components/CmkLabel.vue'

import type { FilterConfigState } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { type ContextFilters, FilterOrigin } from '@/dashboard/types/filter'

import FilterItem from './FilterItem.vue'

type ContextFilterValue = ContextFilters[string]

const props = defineProps<{
  contextFilters: ContextFilters
  objectConfiguredFilters: FilterConfigState

  emptyFiltersTitle: TranslatedString
}>()

const isOverridden = (name: string): boolean => {
  const widgetFilter = props.objectConfiguredFilters[name]
  return !(widgetFilter === undefined || widgetFilter === null)
}

const isPresent = (f: ContextFilterValue | null | undefined): f is ContextFilterValue => f !== null

const dashboardFilters = computed<ContextFilters>(() => {
  const result: ContextFilters = {}
  for (const [name, f] of Object.entries(props.contextFilters) as [
    string,
    ContextFilterValue | null | undefined
  ][]) {
    if (isPresent(f) && f.source === FilterOrigin.DASHBOARD) {
      result[name] = f
    }
  }
  return result
})

const runtimeFilters = computed<ContextFilters>(() => {
  const result: ContextFilters = {}
  for (const [name, f] of Object.entries(props.contextFilters) as [
    string,
    ContextFilterValue | null | undefined
  ][]) {
    if (isPresent(f) && f.source === FilterOrigin.QUICK_FILTER) {
      result[name] = f
    }
  }
  return result
})

const countInheritedFilters = computed(() => {
  return Object.keys(dashboardFilters.value).length + Object.keys(runtimeFilters.value).length
})
</script>

<template>
  <ul v-if="countInheritedFilters > 0" class="db-display-context-filters">
    <li v-for="(filter, name) in dashboardFilters" :key="name">
      <FilterItem
        :origin="FilterOrigin.DASHBOARD"
        :overridden="isOverridden(name)"
        :filter-id="name"
        :configured-values="filter.configuredValues"
      />
    </li>

    <li v-for="(filter, name) in runtimeFilters" :key="name">
      <FilterItem
        :origin="FilterOrigin.QUICK_FILTER"
        :overridden="isOverridden(name)"
        :filter-id="name"
        :configured-values="filter.configuredValues"
      />
    </li>
  </ul>
  <CmkLabel v-else
    ><span class="db-display-context-filters__no-filters">{{
      props.emptyFiltersTitle
    }}</span></CmkLabel
  >
</template>

<style scoped>
.db-display-context-filters {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.db-display-context-filters__no-filters {
  font-size: 12px;
  color: var(--menu-entry-disabled);
}
</style>
