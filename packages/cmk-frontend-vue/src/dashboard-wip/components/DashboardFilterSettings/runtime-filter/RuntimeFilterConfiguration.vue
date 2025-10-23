<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { useFilters } from '@/dashboard-wip/components/filter/composables/useFilters.ts'
import type {
  ConfiguredFilters,
  ConfiguredValues,
  FilterDefinition
} from '@/dashboard-wip/components/filter/types.ts'
import { RuntimeFilterMode } from '@/dashboard-wip/types/filter.ts'

import FilterCollection from '../FilterCollection.vue'
import FilterCollectionInputItem from '../FilterCollectionInputItem.vue'

const { _t } = usei18n()
const props = defineProps<{
  filterDefinitions: Record<string, FilterDefinition>
  runtimeFilters: ReturnType<typeof useFilters>
  dashboardFilters: ConfiguredFilters
  mandatoryFilters: Set<string>
  runtimeFiltersMode: RuntimeFilterMode
  canEdit: boolean
}>()

const emit = defineEmits<{
  'apply-runtime-filters': []
  'set-configuration-target': [target: 'required-filter']
  'update:runtime-filters-mode': [mode: RuntimeFilterMode]
}>()

const showAppliedConfirmation = ref(false)
const overrideMode = ref(props.runtimeFiltersMode === RuntimeFilterMode.OVERRIDE)

watch(
  () => props.runtimeFiltersMode,
  (newMode) => {
    // keep local state in sync if parent updates externally
    overrideMode.value = newMode === RuntimeFilterMode.OVERRIDE
  }
)

watch(overrideMode, (checked) => {
  emit(
    'update:runtime-filters-mode',
    checked ? RuntimeFilterMode.OVERRIDE : RuntimeFilterMode.MERGE
  )
})

const hostRuntimeFilters = computed(() => {
  const filters: string[] = []
  props.runtimeFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = props.filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'host') {
      filters.push(filterId)
    }
  })
  return filters
})

const serviceRuntimeFilters = computed(() => {
  const filters: string[] = []
  props.runtimeFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = props.filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'service') {
      filters.push(filterId)
    }
  })
  return filters
})

const applyRuntimeFilters = () => {
  emit('apply-runtime-filters')
  showAppliedConfirmation.value = true
}

const switchToRequiredConfiguration = () => {
  emit('set-configuration-target', 'required-filter')
}

const handleUpdateFilterValues = (filterId: string, values: ConfiguredValues) => {
  props.runtimeFilters.updateFilterValues(filterId, values)
}

const handleRemoveFilter = (filterId: string) => {
  props.runtimeFilters.removeFilter(filterId)
}

watch(
  () => JSON.stringify(props.runtimeFilters.getFilters()),
  (newVal, oldVal) => {
    if (showAppliedConfirmation.value && newVal !== oldVal) {
      showAppliedConfirmation.value = false
    }
  }
)
</script>

<template>
  <div>
    <div class="filter-configuration__apply">
      <CmkButton variant="primary" @click="applyRuntimeFilters">
        {{ _t('Apply to dashboard') }}
      </CmkButton>
      <CmkButton v-if="canEdit" variant="secondary" @click="switchToRequiredConfiguration">
        {{ _t('Edit required runtime filters') }}
      </CmkButton>
    </div>
    <div class="filter-configuration__mode-toggle">
      <CmkCheckbox v-model="overrideMode" :label="_t('Override dashboard filters')" />
    </div>
    <div v-if="showAppliedConfirmation">
      <CmkAlertBox variant="success">
        <CmkLabel>
          {{ _t('Success! Your runtime filters have been applied') }}
        </CmkLabel>
      </CmkAlertBox>
    </div>
    <FilterCollection
      :title="_t('Host filter')"
      :filters="hostRuntimeFilters"
      :get-filter-values="runtimeFilters.getFilterValues"
      additional-item-label="Select additional filters from list"
    >
      <template #default="{ filterId, configuredFilterValues }">
        <FilterCollectionInputItem
          :filter-id="filterId"
          :configured-filter-values="
            configuredFilterValues !== null
              ? configuredFilterValues
              : dashboardFilters[filterId] || null
          "
          :filter-definitions="filterDefinitions"
          :allow-remove="!mandatoryFilters.has(filterId)"
          :show-required-label="mandatoryFilters.has(filterId)"
          @update-filter-values="handleUpdateFilterValues"
          @remove-filter="handleRemoveFilter"
        />
      </template>
    </FilterCollection>
    <FilterCollection
      :title="_t('Service filter')"
      :filters="serviceRuntimeFilters"
      :get-filter-values="runtimeFilters.getFilterValues"
      additional-item-label="Select additional filters from list"
    >
      <template #default="{ filterId, configuredFilterValues }">
        <FilterCollectionInputItem
          :filter-id="filterId"
          :configured-filter-values="
            configuredFilterValues !== null
              ? configuredFilterValues
              : dashboardFilters[filterId] || null
          "
          :filter-definitions="filterDefinitions"
          :allow-remove="!mandatoryFilters.has(filterId)"
          :show-required-label="mandatoryFilters.has(filterId)"
          @update-filter-values="handleUpdateFilterValues"
          @remove-filter="handleRemoveFilter"
        />
      </template>
    </FilterCollection>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__apply {
  display: flex;
  align-items: center;
  margin-bottom: var(--dimension-5);
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__mode-toggle {
  margin-bottom: var(--dimension-5);
}
</style>
