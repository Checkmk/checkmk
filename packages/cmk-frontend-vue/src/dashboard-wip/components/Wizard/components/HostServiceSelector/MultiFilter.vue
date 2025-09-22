<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import DisplayFilters from '@/dashboard-wip/components/Wizard/components/DisplayFilters/DisplayFilters.vue'
import AddFilterMessage from '@/dashboard-wip/components/Wizard/components/filter/ObjectTypeFilterConfiguration/AddFilterMessage.vue'
import FilterInputItem from '@/dashboard-wip/components/filter/FilterInputItem/FilterInputItem.vue'
import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'

import type { UseAddFilter } from '../AddFilters/composables/useAddFilters'
import GenericFilter from './GenericFilter.vue'
import type { ComponentLabels, GenericFilterLogic } from './types'

const { _t } = usei18n()

interface MultiHostFilterProps extends ComponentLabels {
  dashboardFilters: ConfiguredFilters
  quickFilters: ConfiguredFilters
  widgetFiltersHandler: Filters

  addFilterHandler: UseAddFilter
}

defineProps<MultiHostFilterProps>()
const logicHandler = defineModel<GenericFilterLogic>('logicHandler', { required: true })
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
      <FilterInputItem
        v-for="(configuredValues, name) in logicHandler.widgetFilters.value"
        :key="name"
        :filter-id="name"
        :configured-filter-values="configuredValues"
        @update-filter-values="widgetFiltersHandler.updateFilterValues"
      />

      <AddFilterMessage v-if="addFilterHandler.isOpen.value" />
      <ActionButton
        v-else
        :label="_t('Add filter')"
        :icon="{ name: 'icon-plus', side: 'left' }"
        variant="secondary"
        :action="() => addFilterHandler.open(logicHandler.filterType)"
      />
    </template>
  </GenericFilter>
</template>
