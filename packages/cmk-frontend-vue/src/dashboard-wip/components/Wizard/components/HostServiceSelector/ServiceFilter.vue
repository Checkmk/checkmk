<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import type { UseAddFilter } from '@/dashboard-wip/components/Wizard/components/AddFilters/composables/useAddFilters'
import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'

import { ElementSelection } from '../../types'
import MultiFilter from './MultiFilter.vue'
import SingleMultiChoice from './SingleMultiChoice.vue'
import SpecificServiceFilter from './SpecificServiceFilter.vue'
import type { GenericFilterLogic } from './types'

const { _t } = usei18n()

interface HostFilterProps {
  dashboardFilters: ConfiguredFilters
  quickFilters: ConfiguredFilters
  widgetFilters: Filters

  addFilterHandler: UseAddFilter
}

defineProps<HostFilterProps>()

const serviceSelection = defineModel<ElementSelection>('serviceSelection', {
  default: ElementSelection.SPECIFIC
})
const serviceFilterLogic = defineModel<GenericFilterLogic>('serviceFilterLogic', { required: true })
</script>

<template>
  <SingleMultiChoice
    v-model:mode-selection="serviceSelection"
    :single-elements-label="_t('Specific service')"
    :multiple-elements-label="_t('Multiple services')"
  >
    <template #specific>
      <SpecificServiceFilter
        v-model:logic-handler="serviceFilterLogic"
        :dashboard-filters="dashboardFilters"
        :quick-filters="quickFilters"
        :widget-filters-handler="widgetFilters"
        :global-filters-label="_t('Applied service name filter')"
        :global-filters-tooltip="_t('to be defined')"
        :widget-filters-label="_t('Widget filter')"
        :widget-filters-tooltip="_t('to be defined')"
        :filter-select-placeholder="_t('Select service name')"
        :empty-filters-title="_t('No service name filter applied.')"
        :empty-filters-message="
          _t(
            'A service name filter selected as a dashboard or quick filter in the filters slideout appears here and applies to this widget'
          )
        "
      />
    </template>

    <template #multi>
      <MultiFilter
        v-model:logic-handler="serviceFilterLogic"
        :dashboard-filters="dashboardFilters"
        :quick-filters="quickFilters"
        :widget-filters-handler="widgetFilters"
        :add-filter-handler="addFilterHandler"
        :global-filters-label="_t('Applied service filters')"
        :global-filters-tooltip="_t('to be defined')"
        :widget-filters-label="_t('Widget filter')"
        :widget-filters-tooltip="_t('to be defined')"
        :filter-select-placeholder="_t('Select service name')"
        :empty-filters-title="_t('No host filters applied.')"
        :empty-filters-message="
          _t(
            'Dashboard or quick filters selected in the filters slideout appears here and applies to this widget'
          )
        "
      />
    </template>
  </SingleMultiChoice>
</template>
