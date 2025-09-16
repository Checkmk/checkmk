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
import SpecificHostFilter from './SpecificHostFilter.vue'
import type { GenericFilterLogic } from './types'

const { _t } = usei18n()

interface HostFilterProps {
  dashboardFilters: ConfiguredFilters
  quickFilters: ConfiguredFilters
  widgetFilters: Filters

  addFilterHandler: UseAddFilter
}

defineProps<HostFilterProps>()

const hostFilterLogic = defineModel<GenericFilterLogic>('hostFilterLogic', { required: true })
const hostSelection = defineModel<ElementSelection>('hostSelection', {
  default: ElementSelection.SPECIFIC
})
</script>

<template>
  <SingleMultiChoice
    v-model:mode-selection="hostSelection"
    :single-elements-label="_t('Specific host')"
    :multiple-elements-label="_t('Multiple hosts')"
  >
    <template #specific>
      <SpecificHostFilter
        v-model:logic-handler="hostFilterLogic"
        :dashboard-filters="dashboardFilters"
        :quick-filters="quickFilters"
        :widget-filters-handler="widgetFilters"
        :global-filters-label="_t('Applied host name filter')"
        :global-filters-tooltip="_t('to be defined')"
        :widget-filters-label="_t('Widget filter')"
        :widget-filters-tooltip="_t('to be defined')"
        :filter-select-placeholder="_t('Select host name')"
        :empty-filters-title="_t('No host name filter applied.')"
        :empty-filters-message="
          _t(
            'A host name filter selected as a dashboard or quick filter in the filters slideout appears here and applies to this widget'
          )
        "
      />
    </template>

    <template #multi>
      <MultiFilter
        v-model:logic-handler="hostFilterLogic"
        :dashboard-filters="dashboardFilters"
        :quick-filters="quickFilters"
        :widget-filters-handler="widgetFilters"
        :add-filter-handler="addFilterHandler"
        :global-filters-label="_t('Applied host filters')"
        :global-filters-tooltip="_t('to be defined')"
        :widget-filters-label="_t('Widget filter')"
        :widget-filters-tooltip="_t('to be defined')"
        :filter-select-placeholder="_t('Select host name')"
        :empty-filters-title="_t('No host filters applied.')"
        :empty-filters-message="
          _t(
            'Dashboard or quick filters selected in the filters slideout appear here and apply to this widget'
          )
        "
      />
    </template>
  </SingleMultiChoice>
</template>
