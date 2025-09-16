<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'

import SpecificHostFilter from './SpecificHostFilter.vue'
import type { GenericFilterLogic } from './types'

const { _t } = usei18n()

interface HostFilterProps {
  widgetFilters: Filters
}

defineProps<HostFilterProps>()

const hostFilterLogic = defineModel<GenericFilterLogic>('hostFilterLogic', { required: true })
</script>

<template>
  <SpecificHostFilter
    v-model:logic-handler="hostFilterLogic"
    :dashboard-filters="{}"
    :quick-filters="{}"
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
