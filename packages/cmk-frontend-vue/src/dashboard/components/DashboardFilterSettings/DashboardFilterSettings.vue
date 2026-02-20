<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkSlideIn from '@/components/CmkSlideIn'

import FilterSettings from '@/dashboard/components/DashboardFilterSettings/FilterSettings.vue'
import type {
  FilterSettingsEmits,
  FilterSettingsProps
} from '@/dashboard/components/DashboardFilterSettings/types.ts'

interface Props extends FilterSettingsProps {
  open: boolean
}

defineProps<Props>()
const { _t } = usei18n()
const emit = defineEmits<FilterSettingsEmits>()
</script>

<template>
  <CmkSlideIn
    :open="open"
    :stack-priority="-10"
    class="db-filter-settings__slide-in"
    :aria-label="_t('Dashboard filter')"
    @close="emit('close')"
  >
    <FilterSettings
      :can-edit="canEdit"
      :is-built-in="isBuiltIn"
      :applied-runtime-filters="appliedRuntimeFilters"
      :configured-dashboard-filters="configuredDashboardFilters"
      :configured-mandatory-runtime-filters="configuredMandatoryRuntimeFilters"
      :configured-runtime-filters-mode="configuredRuntimeFiltersMode"
      :starting-window="startingWindow"
      @apply-runtime-filters="(filters, mode) => emit('apply-runtime-filters', filters, mode)"
      @close="emit('close')"
      @save-filter-settings="(payload) => emit('save-filter-settings', payload)"
    />
  </CmkSlideIn>
</template>

<style scoped>
.db-filter-settings__slide-in {
  /* Hack to keep the filters slide in above the add widget one */
  z-index: calc(var(--z-index-modal) + 1);
}
</style>
