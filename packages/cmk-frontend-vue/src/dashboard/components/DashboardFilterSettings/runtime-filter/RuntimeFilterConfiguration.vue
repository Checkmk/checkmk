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

import type { useFilters } from '@/dashboard/components/filter/composables/useFilters.ts'
import type {
  ConfiguredFilters,
  ConfiguredValues,
  FilterDefinition
} from '@/dashboard/components/filter/types.ts'
import { isFullyConfiguredFilter } from '@/dashboard/components/filter/utils.ts'
import { RuntimeFilterMode } from '@/dashboard/types/filter.ts'

import FilterCollectionInputItem from '../FilterCollectionInputItem.vue'
import RuntimeFilterCollection from './RuntimeFilterCollection.vue'

const { _t } = usei18n()
const props = defineProps<{
  filterDefinitions: Record<string, FilterDefinition>
  runtimeFilters: ReturnType<typeof useFilters>
  dashboardFilters: ConfiguredFilters
  hostDashboardFilters: string[]
  serviceDashboardFilters: string[]
  mandatoryFilters: Set<string>
  runtimeFiltersMode: RuntimeFilterMode
  canEdit: boolean
  isBuiltIn: boolean
  resetKey: number
}>()

const emit = defineEmits<{
  'apply-runtime-filters': []
  'open-configuration': []
  'update:runtime-filters-mode': [mode: RuntimeFilterMode]
  'reset-runtime-filters': []
}>()

const editButtonTooltip = computed(() => {
  if (props.isBuiltIn) {
    return _t('Editing is disabled for built-in dashboards')
  }
  if (!props.canEdit) {
    return _t('Edit access required')
  }
  return undefined
})

const misconfiguredFilters = ref<string[]>([])
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
  const filters = props.runtimeFilters.getFilters()
  const notFullyConfigured: string[] = []

  Object.keys(filters).forEach((filterId) => {
    const filterValues = filters[filterId]!
    const filterDef = props.filterDefinitions[filterId]
    if (filterDef && !isFullyConfiguredFilter(filterValues, filterDef)) {
      notFullyConfigured.push(filterDef.title!)
    }
  })

  if (notFullyConfigured.length > 0) {
    misconfiguredFilters.value = notFullyConfigured
    showAppliedConfirmation.value = false
    return
  }

  misconfiguredFilters.value = []
  showAppliedConfirmation.value = true
  emit('apply-runtime-filters')
}

watch(
  () => JSON.stringify(props.runtimeFilters.getFilters()),
  (newVal, oldVal) => {
    if (newVal !== oldVal) {
      showAppliedConfirmation.value = false
      misconfiguredFilters.value = []
    }
  }
)

const resetRuntimeFilters = () => {
  emit('reset-runtime-filters')
}

const openConfiguration = () => {
  emit('open-configuration')
}

const handleUpdateFilterValues = (filterId: string, values: ConfiguredValues) => {
  props.runtimeFilters.updateFilterValues(filterId, values)
}

const handleRemoveFilter = (filterId: string) => {
  props.runtimeFilters.removeFilter(filterId)
}
</script>

<template>
  <div class="db-runtime-filter-configuration__actions">
    <div class="db-runtime-filter-configuration__actions-left">
      <CmkButton variant="primary" @click="applyRuntimeFilters">
        {{ _t('Apply') }}
      </CmkButton>
      <CmkButton variant="optional" @click="resetRuntimeFilters">
        {{ _t('Reset to pre-selected filters') }}
      </CmkButton>
    </div>
    <CmkButton
      :disabled="!canEdit || isBuiltIn"
      variant="optional"
      :title="editButtonTooltip"
      @click="openConfiguration"
    >
      {{ _t('Edit filter settings') }}
    </CmkButton>
  </div>

  <CmkCheckbox v-model="overrideMode" :label="_t('Override default filters')" />

  <div>
    <CmkAlertBox v-if="misconfiguredFilters.length > 0" variant="error">
      <CmkLabel>
        {{ _t('Please configure the following filters: ') }}
        {{ misconfiguredFilters.join(', ') }}
      </CmkLabel>
    </CmkAlertBox>
    <CmkAlertBox v-else-if="showAppliedConfirmation" variant="success">
      <CmkLabel>
        {{ _t('Success! Your runtime filters have been applied') }}
      </CmkLabel>
    </CmkAlertBox>
  </div>

  <RuntimeFilterCollection
    object-type="host"
    :filters="hostRuntimeFilters"
    :get-filter-values="runtimeFilters.getFilterValues"
    :additional-item-label="_t('Add filter from left panel')"
    :dashboard-filters="hostDashboardFilters"
    :dashboard-configured-filters="dashboardFilters"
    :force-override="overrideMode"
  >
    <template #default="{ filterId, configuredFilterValues }">
      <FilterCollectionInputItem
        :key="`${filterId}-${props.resetKey}`"
        :filter-id="filterId"
        :configured-filter-values="
          configuredFilterValues !== null
            ? configuredFilterValues
            : dashboardFilters[filterId] || null
        "
        :filter-definitions="filterDefinitions"
        :allow-remove="!mandatoryFilters.has(filterId)"
        :show-required-label="mandatoryFilters.has(filterId)"
        :label="mandatoryFilters.has(filterId) ? _t('pre-selected') : undefined"
        @update-filter-values="handleUpdateFilterValues"
        @remove-filter="handleRemoveFilter"
      />
    </template>
  </RuntimeFilterCollection>

  <RuntimeFilterCollection
    object-type="service"
    :filters="serviceRuntimeFilters"
    :get-filter-values="runtimeFilters.getFilterValues"
    :additional-item-label="_t('Add filter from left panel')"
    :dashboard-filters="serviceDashboardFilters"
    :dashboard-configured-filters="dashboardFilters"
    :force-override="overrideMode"
  >
    <template #default="{ filterId, configuredFilterValues }">
      <FilterCollectionInputItem
        :key="`${filterId}-${props.resetKey}`"
        :filter-id="filterId"
        :configured-filter-values="
          configuredFilterValues !== null
            ? configuredFilterValues
            : dashboardFilters[filterId] || null
        "
        :filter-definitions="filterDefinitions"
        :allow-remove="!mandatoryFilters.has(filterId)"
        :show-required-label="mandatoryFilters.has(filterId)"
        :label="mandatoryFilters.has(filterId) ? _t('Pre-selected') : undefined"
        @update-filter-values="handleUpdateFilterValues"
        @remove-filter="handleRemoveFilter"
      />
    </template>
  </RuntimeFilterCollection>
</template>

<style scoped>
.db-runtime-filter-configuration__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.db-runtime-filter-configuration__actions-left {
  display: flex;
  gap: var(--dimension-4);
}
</style>
