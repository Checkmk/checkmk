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
import CmkIcon from '@/components/CmkIcon'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkTab from '@/components/CmkTabs/CmkTab.vue'
import CmkTabContent from '@/components/CmkTabs/CmkTabContent.vue'
import CmkTabs from '@/components/CmkTabs/CmkTabs.vue'

import type {
  FilterSettingsEmits,
  FilterSettingsProps
} from '@/dashboard-wip/components/DashboardFilterSettings/types.ts'
import FilterDisplayItem from '@/dashboard-wip/components/filter/FilterDisplayItem/FilterDisplayItem.vue'
import FilterSelection from '@/dashboard-wip/components/filter/FilterSelection/FilterSelection.vue'
import { CATEGORY_DEFINITIONS } from '@/dashboard-wip/components/filter/FilterSelection/utils.ts'
import { useFilters } from '@/dashboard-wip/components/filter/composables/useFilters.ts'
import { parseFilterTypes, useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'

import FilterCollection from './FilterCollection.vue'
import FilterCollectionInputItem from './FilterCollectionInputItem.vue'
import RequiredFilterConfiguration from './runtime-filter/RequiredFilterConfiguration.vue'
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

const saveDashboardFilters = () => {
  console.log('Sending dashboard filters from menu', dashboardFilters.getFilters())
  emit('save-dashboard-filters', dashboardFilters.getFilters())
  showSavedDashboardAlert.value = true
}

const resetDashboardFilters = () => {
  dashboardFilters.setFilters(props.configuredDashboardFilters)
}

const applyRuntimeFilters = () => {
  console.log('Sending runtime filters from menu')
  emit('apply-runtime-filters', runtimeFilters.getFilters())
}

const filterCategories = parseFilterTypes(filterDefinitions, new Set(['host', 'service']))

const showSavedDashboardAlert = ref(false)
const dashboardFilters = useFilters(props.configuredDashboardFilters)

const appliedRuntimeFilterIds = Object.keys(props.appliedRuntimeFilters || {})
const mandatorySet = new Set(props.configuredMandatoryRuntimeFilters)
const nonMandatoryApplied = appliedRuntimeFilterIds.filter(
  (filterId) => !mandatorySet.has(filterId)
)
const mergedRuntimeFilterIds = [...props.configuredMandatoryRuntimeFilters, ...nonMandatoryApplied]

const runtimeFilters = useFilters(props.appliedRuntimeFilters, mergedRuntimeFilterIds)
const mandatoryRuntimeFilters = useFilters(undefined, props.configuredMandatoryRuntimeFilters)
const mandatoryRuntimeFiltersBackup = ref<string[]>([...props.configuredMandatoryRuntimeFilters])

const openedTab = ref<string | number>('dashboard-filter')
const runtimeFilterConfigurationTarget = ref<'runtime-filter' | 'required-filter'>('runtime-filter')

const tabs: {
  id: string
  title: string
}[] = [
  {
    id: 'dashboard-filter',
    title: 'Dashboard filters'
  },
  {
    id: 'runtime-filter',
    title: 'Runtime filters'
  }
]

const targetFilters = computed(() => {
  switch (openedTab.value) {
    case 'dashboard-filter':
      return dashboardFilters
    case 'runtime-filter':
      return runtimeFilterConfigurationTarget.value === 'runtime-filter'
        ? runtimeFilters
        : mandatoryRuntimeFilters
    default:
      return runtimeFilters
  }
})

const isFilterSelectionDisabled = computed(() => {
  return !props.canEdit && openedTab.value === 'dashboard-filter'
})

const setRuntimeFilterConfigurationTarget = (target: 'runtime-filter' | 'required-filter') => {
  runtimeFilterConfigurationTarget.value = target
}

const handleSaveRequiredFilters = () => {
  console.log('Saving runtime filters:', mandatoryRuntimeFilters.getSelectedFilters())
  mandatoryRuntimeFiltersBackup.value = [...mandatoryRuntimeFilters.getSelectedFilters()]

  const currentRuntimeFilters = new Set(runtimeFilters.getSelectedFilters())
  const mandatoryFilters = new Set(mandatoryRuntimeFilters.getSelectedFilters())

  const allRequiredFilters = new Set([...currentRuntimeFilters, ...mandatoryFilters])
  runtimeFilters.resetThroughSelectedFilters([...allRequiredFilters])

  runtimeFilterConfigurationTarget.value = 'runtime-filter'
  console.log('Emit save mandatory runtime filters')
  emit('save-mandatory-runtime-filters', mandatoryRuntimeFilters.getSelectedFilters())
}

const handleCancelRequiredFilters = () => {
  // Restore from backup and return to runtime filter view
  mandatoryRuntimeFilters.resetThroughSelectedFilters([...mandatoryRuntimeFiltersBackup.value])
  runtimeFilterConfigurationTarget.value = 'runtime-filter'
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

watch(
  () => JSON.stringify(dashboardFilters.getFilters()),
  (newVal, oldVal) => {
    // if alert is visible and the filters changed, hide the alert
    if (showSavedDashboardAlert.value && newVal !== oldVal) {
      showSavedDashboardAlert.value = false
    }
  }
)
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

          <!-- Overlay when disabled -->
          <div v-if="isFilterSelectionDisabled" class="filter-selection__disabled-overlay"></div>
        </div>
      </div>
      <div class="filter-configuration__definition-container">
        <div class="filter-configuration__header">
          <CmkLabel variant="title">
            {{ _t('Dashboard filter') }}
          </CmkLabel>
          <button
            class="filter-configuration__close-button"
            type="button"
            :aria-label="_t('Close filter configuration')"
            @click="closeWindow"
          >
            <CmkIcon :aria-label="_t('Clear search')" name="close" size="xxsmall" />
          </button>
        </div>
        <CmkTabs v-model="openedTab">
          <template #tabs>
            <CmkTab v-for="tab in tabs" :id="tab.id" :key="tab.id" class="cmk-demo-tabs">
              {{ tab.title }}
            </CmkTab>
          </template>
          <template #tab-contents>
            <CmkTabContent id="dashboard-filter">
              <div v-if="!canEdit">
                <div class="filter-configuration__owner-message">
                  <CmkLabel variant="title">
                    {{ _t('Filters included by dashboard owner') }}</CmkLabel
                  >
                  <CmkLabel>
                    {{ _t('You can override these by adding a quick filter') }}
                  </CmkLabel>
                </div>
                <FilterCollection
                  :title="_t('Host filter')"
                  :filters="hostDashboardFilters"
                  :get-filter-values="dashboardFilters.getFilterValues"
                  :additional-item-label="_t('Select from list')"
                >
                  <template #default="{ filterId, configuredFilterValues }">
                    <div class="filter-collection-item__container">
                      <FilterDisplayItem
                        :filter-id="filterId"
                        :configured-values="configuredFilterValues!"
                      />
                    </div>
                  </template>
                </FilterCollection>
                <FilterCollection
                  :title="_t('Service filter')"
                  :filters="serviceDashboardFilters"
                  :get-filter-values="dashboardFilters.getFilterValues"
                  additional-item-label="Select from list"
                >
                  <template #default="{ filterId, configuredFilterValues }">
                    <div class="filter-collection-item__container">
                      <FilterDisplayItem
                        :filter-id="filterId"
                        :configured-values="configuredFilterValues!"
                      />
                    </div>
                  </template>
                </FilterCollection>
              </div>
              <div v-else>
                <div class="filter-configuration__apply">
                  <CmkButton variant="primary" @click="saveDashboardFilters">
                    {{ _t('Save') }}</CmkButton
                  >
                  <CmkButton variant="secondary" @click="resetDashboardFilters">
                    {{ _t('Reset to saved filters') }}
                  </CmkButton>
                </div>
                <div v-if="showSavedDashboardAlert">
                  <CmkAlertBox variant="success">
                    <CmkLabel>
                      {{ _t('Success! Your new dashboard filters have been saved') }}
                    </CmkLabel>
                  </CmkAlertBox>
                </div>

                <FilterCollection
                  :title="_t('Host filter')"
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
                  :title="_t('Service filter')"
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
            <CmkTabContent id="runtime-filter">
              <div>
                <CmkAlertBox variant="info">
                  <CmkLabel>
                    {{ _t('Runtime filters are required to load data.') }}
                  </CmkLabel>
                  <CmkLabel>
                    {{ _t('Values apply across all widgets.') }}
                  </CmkLabel>
                </CmkAlertBox>
              </div>

              <RuntimeFilterConfiguration
                v-if="runtimeFilterConfigurationTarget === 'runtime-filter'"
                :filter-definitions="filterDefinitions"
                :runtime-filters="runtimeFilters"
                :dashboard-filters="dashboardFilters.getFilters()"
                :mandatory-filters="new Set(mandatoryRuntimeFilters.getSelectedFilters())"
                @apply-runtime-filters="applyRuntimeFilters"
                @set-configuration-target="setRuntimeFilterConfigurationTarget"
              />

              <RequiredFilterConfiguration
                v-if="runtimeFilterConfigurationTarget === 'required-filter'"
                :filter-definitions="filterDefinitions"
                :runtime-filters="mandatoryRuntimeFilters"
                @save-runtime-filters="handleSaveRequiredFilters"
                @cancel-runtime-filters="handleCancelRequiredFilters"
                @set-configuration-target="setRuntimeFilterConfigurationTarget"
              />
            </CmkTabContent>
          </template>
        </CmkTabs>
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
.filter-configuration__apply {
  display: flex;
  align-items: center;
  margin-bottom: var(--dimension-5);
  gap: var(--dimension-4);
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
.filter-configuration__owner-message {
  margin-bottom: var(--dimension-4);
  padding: var(--dimension-3);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-collection-item__container {
  padding: var(--dimension-7);
  position: relative;
  display: block;
}
</style>
