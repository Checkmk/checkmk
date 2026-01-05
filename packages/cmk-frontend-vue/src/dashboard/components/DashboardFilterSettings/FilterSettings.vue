<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'

import type {
  FilterSettingsEmits,
  FilterSettingsProps
} from '@/dashboard/components/DashboardFilterSettings/types.ts'
import FilterSelection from '@/dashboard/components/filter/FilterSelection/FilterSelection.vue'
import { CATEGORY_DEFINITIONS } from '@/dashboard/components/filter/FilterSelection/utils.ts'
import { useFilters } from '@/dashboard/components/filter/composables/useFilters.ts'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types.ts'
import { parseFilterTypes, useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import type { RuntimeFilterMode } from '@/dashboard/types/filter.ts'

import FilterCollection from './FilterCollection.vue'
import FilterCollectionInputItem from './FilterCollectionInputItem.vue'
import FilterSelectionCollection from './runtime-filter/FilterSelectionCollection.vue'
import RuntimeFilterConfiguration from './runtime-filter/RuntimeFilterConfiguration.vue'

const props = defineProps<FilterSettingsProps>()

const { _t } = usei18n()
const filterDefinitions = useFilterDefinitions()

if (!filterDefinitions) {
  console.error('Filter definitions not found in the provided context')
  throw new Error('Filter definitions are not available')
}

const emit = defineEmits<FilterSettingsEmits>()

const closeWindow = () => {
  emit('close')
}

const applyRuntimeFilters = () => {
  emit('apply-runtime-filters', runtimeFilters.getFilters(), runtimeFiltersMode.value)
}

const filterCategories = parseFilterTypes(filterDefinitions, new Set(['host', 'service']))

const runtimeFiltersMode = ref<RuntimeFilterMode>(props.configuredRuntimeFiltersMode)
const dashboardFilters = useFilters(props.configuredDashboardFilters)

const appliedRuntimeFilterIds = Object.keys(props.appliedRuntimeFilters || {})
const mandatorySet = new Set(props.configuredMandatoryRuntimeFilters)
const nonMandatoryApplied = appliedRuntimeFilterIds.filter(
  (filterId) => !mandatorySet.has(filterId)
)
const mergedRuntimeFilterIds = [...props.configuredMandatoryRuntimeFilters, ...nonMandatoryApplied]

const runtimeFilters = useFilters(props.appliedRuntimeFilters, mergedRuntimeFilterIds)
const initialRuntimeFilters = ref<ConfiguredFilters>(
  JSON.parse(JSON.stringify(runtimeFilters.getFilters()))
)
const mandatoryRuntimeFilters = useFilters(undefined, props.configuredMandatoryRuntimeFilters)

// Track whether the configuration sub-window is open
const isConfigurationWindowOpen = ref(props.startingWindow === 'filter-configuration')
const configurationTab = ref<string | number>('dashboard-filter')

const configurationTabs: {
  id: string
  title: string
}[] = [
  {
    id: 'dashboard-filter',
    title: 'Dashboard filter setup'
  },
  {
    id: 'required-filter',
    title: 'Runtime filter setup'
  }
]

const targetFilters = computed(() => {
  if (!isConfigurationWindowOpen.value) {
    return runtimeFilters
  }
  switch (configurationTab.value) {
    case 'dashboard-filter':
      return dashboardFilters
    case 'required-filter':
      return mandatoryRuntimeFilters
    default:
      return dashboardFilters
  }
})

const openConfigurationWindow = () => {
  isConfigurationWindowOpen.value = true
  configurationTab.value = 'dashboard-filter'
}

const handleUpdateRuntimeFiltersMode = (mode: RuntimeFilterMode) => {
  runtimeFiltersMode.value = mode
}

const handleResetRuntimeFilters = () => {
  const activeFilters = [...runtimeFilters.getSelectedFilters()]
  activeFilters.forEach((filterId) => {
    if (!mandatorySet.has(filterId)) {
      runtimeFilters.removeFilter(filterId)
    }
  })
}

const handleSaveConfiguration = () => {
  const mandatorySelectedFilters = mandatoryRuntimeFilters.getSelectedFilters()
  emit('save-filter-settings', {
    dashboardFilters: dashboardFilters.getFilters(),
    mandatoryRuntimeFilters: mandatorySelectedFilters
  })

  // Set runtime filters
  const currentRuntimeFilters = new Set(runtimeFilters.getSelectedFilters())
  const mandatoryFilters = new Set(mandatorySelectedFilters)
  const allRequiredFilters = new Set([...currentRuntimeFilters, ...mandatoryFilters])
  runtimeFilters.resetThroughSelectedFilters([...allRequiredFilters])

  initialRuntimeFilters.value = JSON.parse(JSON.stringify(runtimeFilters.getFilters()))

  isConfigurationWindowOpen.value = false
}

const handleCancelConfiguration = () => {
  // Restore from props
  mandatoryRuntimeFilters.resetThroughSelectedFilters([...props.configuredMandatoryRuntimeFilters])
  dashboardFilters.setFilters(JSON.parse(JSON.stringify(props.configuredDashboardFilters)))
  runtimeFilters.setFilters(JSON.parse(JSON.stringify(initialRuntimeFilters.value)))
  isConfigurationWindowOpen.value = false
}

const hostDashboardFilters = computed(() => {
  const filters: string[] = []
  dashboardFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'host') {
      filters.push(filterId)
    }
  })
  return filters
})

const serviceDashboardFilters = computed(() => {
  const filters: string[] = []
  dashboardFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'service') {
      filters.push(filterId)
    }
  })
  return filters
})

const hostMandatoryFilters = computed(() => {
  const filters: string[] = []
  mandatoryRuntimeFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'host') {
      filters.push(filterId)
    }
  })
  return filters
})

const serviceMandatoryFilters = computed(() => {
  const filters: string[] = []
  mandatoryRuntimeFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'service') {
      filters.push(filterId)
    }
  })
  return filters
})
</script>

<template>
  <div class="filter-configuration__external-container">
    <div class="filter-configuration__main-container">
      <div class="filter-configuration__selection-container">
        <div class="filter-selections__wrapper">
          <FilterSelection
            :category-filter="filterCategories.get('host')!"
            :category-definition="CATEGORY_DEFINITIONS.host!"
            :filters="targetFilters"
            class="filter-selection__item"
          />
          <FilterSelection
            :category-filter="filterCategories.get('service')!"
            :category-definition="CATEGORY_DEFINITIONS.service!"
            :filters="targetFilters"
            class="filter-selection__item"
          />
        </div>
      </div>
      <div class="filter-configuration__definition-container">
        <div class="filter-configuration__header">
          <div class="filter-configuration__window-title">
            {{ isConfigurationWindowOpen ? _t('Filter configuration') : _t('Runtime filters') }}
          </div>
          <button
            class="filter-configuration__close-button"
            type="button"
            :aria-label="_t('Close filter configuration')"
            @click="closeWindow"
          >
            <CmkIcon :aria-label="_t('Clear search')" name="close" size="xxsmall" />
          </button>
        </div>

        <div v-if="!isConfigurationWindowOpen">
          <div class="runtime-filter-info">
            <div class="filter-configuration__title">
              {{ _t('Runtime filters are required to load data.') }}
            </div>
            <div class="filter-configuration__subtitle">
              {{ _t('Values are temporary and can be overridden by widget filters.') }}
            </div>
          </div>

          <RuntimeFilterConfiguration
            :filter-definitions="filterDefinitions"
            :runtime-filters="runtimeFilters"
            :dashboard-filters="dashboardFilters.getFilters()"
            :host-dashboard-filters="hostDashboardFilters"
            :service-dashboard-filters="serviceDashboardFilters"
            :mandatory-filters="new Set(mandatoryRuntimeFilters.getSelectedFilters())"
            :runtime-filters-mode="runtimeFiltersMode"
            :can-edit="canEdit"
            @update:runtime-filters-mode="handleUpdateRuntimeFiltersMode"
            @apply-runtime-filters="applyRuntimeFilters"
            @open-configuration="openConfigurationWindow"
            @reset-runtime-filters="handleResetRuntimeFilters"
          />
        </div>

        <div v-else class="configuration-subwindow">
          <div class="configuration-subwindow__actions">
            <CmkButton variant="primary" @click="handleSaveConfiguration">
              {{ _t('Save') }}
            </CmkButton>
            <CmkButton variant="secondary" class="cancel-button" @click="handleCancelConfiguration">
              <CmkIcon name="cancel" size="xsmall" />
              {{ _t('Cancel') }}
            </CmkButton>
          </div>

          <CmkTabs v-model="configurationTab">
            <template #tabs>
              <CmkTab
                v-for="tab in configurationTabs"
                :id="tab.id"
                :key="tab.id"
                class="cmk-demo-tabs"
              >
                {{ tab.title }}
              </CmkTab>
            </template>
            <template #tab-contents>
              <CmkTabContent id="dashboard-filter">
                <div>
                  <div class="filter-configuration__info-header">
                    <div class="filter-configuration__title">
                      {{ _t('Set filters for all widgets.') }}
                    </div>
                    <div class="filter-configuration__subtitle">
                      {{ _t('Values can be overridden by runtime or widget filters.') }}
                    </div>
                  </div>
                  <hr class="cmk-hr" />

                  <FilterCollection
                    :title="_t('Host filters')"
                    :filters="hostDashboardFilters"
                    :get-filter-values="dashboardFilters.getFilterValues"
                    additional-item-label="Select from list"
                  >
                    <template #default="{ filterId, configuredFilterValues }">
                      <FilterCollectionInputItem
                        :filter-id="filterId"
                        :configured-filter-values="configuredFilterValues"
                        :filter-definitions="filterDefinitions"
                        @update-filter-values="dashboardFilters.updateFilterValues"
                        @remove-filter="dashboardFilters.removeFilter"
                      />
                    </template>
                  </FilterCollection>
                  <FilterCollection
                    :title="_t('Service filters')"
                    :filters="serviceDashboardFilters"
                    :get-filter-values="dashboardFilters.getFilterValues"
                    additional-item-label="Select from list"
                  >
                    <template #default="{ filterId, configuredFilterValues }">
                      <FilterCollectionInputItem
                        :filter-id="filterId"
                        :configured-filter-values="configuredFilterValues"
                        :filter-definitions="filterDefinitions"
                        @update-filter-values="dashboardFilters.updateFilterValues"
                        @remove-filter="dashboardFilters.removeFilter"
                      />
                    </template>
                  </FilterCollection>
                </div>
              </CmkTabContent>

              <CmkTabContent id="required-filter">
                <div class="required-filters-content">
                  <div class="filter-configuration__info-header">
                    <div class="filter-configuration__title">
                      {{ _t('Set required filters for viewers to enter on load.') }}
                    </div>
                    <div class="filter-configuration__subtitle">
                      {{ _t('Values are temporary and can be overridden by widget filters.') }}
                    </div>
                  </div>
                  <hr class="cmk-hr" />

                  <FilterSelectionCollection
                    :title="_t('Host filters')"
                    :filters="hostMandatoryFilters"
                    :filter-definitions="filterDefinitions"
                    @remove-filter="mandatoryRuntimeFilters.removeFilter"
                  />
                  <FilterSelectionCollection
                    :title="_t('Service filters')"
                    :filters="serviceMandatoryFilters"
                    :filter-definitions="filterDefinitions"
                    @remove-filter="mandatoryRuntimeFilters.removeFilter"
                  />
                </div>
              </CmkTabContent>
            </template>
          </CmkTabs>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__external-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__main-container {
  background-color: var(--ux-theme-2);
  display: flex;
  width: 100%;
  flex: 1;
  height: 100%;
  column-gap: 10px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__selection-container {
  flex: 1.3;
  height: 100%;
  background-color: var(--slide-in-left-part);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-selections__wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: var(--dimension-4);
  position: relative;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-selection__item {
  flex: 1;
  min-height: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-selection__disabled-overlay {
  position: absolute;
  inset: 0;
  background-color: var(--color-conference-grey-60);
  z-index: 10;
  pointer-events: auto;
  cursor: not-allowed;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__definition-container {
  background-color: var(--ux-theme-1);
  flex: 2;
  width: 100%;
  height: 100vh;
  padding: var(--dimension-7);
  overflow-y: auto;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__header {
  margin-bottom: var(--dimension-5);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__close-button {
  background: none;
  border: none;
  color: var(--font-color);
  cursor: pointer;
  margin: 0;
  padding: 0;
  font-size: var(--dimension-6);
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.runtime-filter-info {
  margin-bottom: var(--dimension-5);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.configuration-subwindow__actions {
  display: flex;
  align-items: center;
  margin-bottom: var(--dimension-5);
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__info-header {
  margin-top: var(--dimension-4);
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-hr {
  border: none;
  border-top: 1px solid var(--ux-theme-5);
  margin: var(--dimension-5) 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.required-filters-content {
  margin-top: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__window-title {
  font-size: var(--dimension-6);
  color: var(--font-color);
  font-weight: var(--font-weight-bold);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__title {
  font-size: 14px;
  color: var(--font-color);
  font-weight: var(--font-weight-bold);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__subtitle {
  font-size: var(--dimension-5);
  color: var(--font-color);
  margin-top: var(--dimension-1);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cancel-button {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
