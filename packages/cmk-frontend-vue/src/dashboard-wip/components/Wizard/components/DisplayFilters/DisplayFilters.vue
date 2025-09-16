<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkDialog from '@/components/CmkDialog.vue'

import { FilterOrigin } from '@/dashboard-wip/components/Wizard/components/HostServiceSelector/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'

import FilterItem from './FilterItem.vue'

interface DisplayFiltersProp {
  dashboardFilters?: ConfiguredFilters
  quickFilters?: ConfiguredFilters
  widgetFilters?: ConfiguredFilters

  emptyFiltersTitle: TranslatedString
  emptyFiltersMessage: TranslatedString
}

const props = withDefaults(defineProps<DisplayFiltersProp>(), {
  dashboardFilters: () => {
    return {} as ConfiguredFilters
  },
  quickFilters: () => {
    return {} as ConfiguredFilters
  },
  widgetFilters: () => {
    return {} as ConfiguredFilters
  }
})

const isOverriden = (name: string): boolean => {
  return name in props.widgetFilters
}

const countInheritedFilters = computed(() => {
  return Object.keys(props.dashboardFilters).length + Object.keys(props.quickFilters).length
})
</script>

<template>
  <ul v-if="countInheritedFilters > 0" class="db-display-filters__list">
    <li v-for="(configuredValues, name) in dashboardFilters" :key="name">
      <FilterItem
        :origin="FilterOrigin.DASHBOARD"
        :overridden="isOverriden(name)"
        :filter-id="name"
        :configured-values="configuredValues"
      />
    </li>

    <li v-for="(configuredValues, name) in quickFilters" :key="name">
      <FilterItem
        :origin="FilterOrigin.QUICK_FILTER"
        :overridden="isOverriden(name)"
        :filter-id="name"
        :configured-values="configuredValues"
      />
    </li>
  </ul>

  <CmkDialog v-else :title="props.emptyFiltersTitle" :message="props.emptyFiltersMessage" />
</template>

<style scoped>
.db-display-filters__list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}
</style>
