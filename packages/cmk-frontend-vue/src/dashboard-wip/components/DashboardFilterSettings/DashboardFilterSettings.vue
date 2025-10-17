<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import FilterSettings from '@/dashboard-wip/components/DashboardFilterSettings/FilterSettings.vue'
import type {
  FilterSettingsEmits,
  FilterSettingsProps
} from '@/dashboard-wip/components/DashboardFilterSettings/types.ts'

interface Props extends FilterSettingsProps {
  open: boolean
}

defineProps<Props>()
const emit = defineEmits<FilterSettingsEmits>()
</script>

<template>
  <CmkSlideIn :open="open" @close="emit('close')">
    <FilterSettings
      :starting-tab="startingTab"
      :can-edit="canEdit"
      :applied-runtime-filters="appliedRuntimeFilters"
      :configured-dashboard-filters="configuredDashboardFilters"
      :configured-mandatory-runtime-filters="configuredMandatoryRuntimeFilters"
      :configured-runtime-filters-mode="configuredRuntimeFiltersMode"
      @apply-runtime-filters="(filters, mode) => emit('apply-runtime-filters', filters, mode)"
      @close="emit('close')"
      @save-dashboard-filters="emit('save-dashboard-filters', $event)"
      @save-mandatory-runtime-filters="emit('save-mandatory-runtime-filters', $event)"
    />
  </CmkSlideIn>
</template>
