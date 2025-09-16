<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import DisplayFilters from '@/dashboard-wip/components/Wizard/components/DisplayFilters/DisplayFilters.vue'
import AutocompleteService from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteService.vue'
import { type Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'

import GenericFilter from './GenericFilter.vue'
import type { ComponentLabels, GenericFilterLogic } from './types'

interface SpecificHostFilterProps extends ComponentLabels {
  dashboardFilters: ConfiguredFilters
  quickFilters: ConfiguredFilters
  widgetFiltersHandler: Filters
}

const logicHandler = defineModel<GenericFilterLogic>('logicHandler', { required: true })
defineProps<SpecificHostFilterProps>()
</script>

<template>
  <GenericFilter
    :global-filters-label="globalFiltersLabel"
    :global-filter-tooltip="globalFiltersTooltip"
    :widget-filter-label="widgetFiltersLabel"
    :widget-filter-tooltip="widgetFiltersTooltip"
  >
    <template #global-filters>
      <DisplayFilters
        :dashboard-filters="dashboardFilters"
        :quick-filters="quickFilters"
        :widget-filters="logicHandler.widgetFilters.value"
        :empty-filters-title="emptyFiltersTitle"
        :empty-filters-message="emptyFiltersMessage"
      />
    </template>
    <template #widget-filters>
      <AutocompleteService v-model:service-description="logicHandler.exactMatchFilterValue.value" />
    </template>
  </GenericFilter>
</template>
