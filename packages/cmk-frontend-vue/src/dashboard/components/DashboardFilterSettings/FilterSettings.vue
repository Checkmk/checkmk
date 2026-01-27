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
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

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
const mandatorySet = computed(() => new Set(props.configuredMandatoryRuntimeFilters))
const nonMandatoryApplied = appliedRuntimeFilterIds.filter(
  (filterId) => !mandatorySet.value.has(filterId)
)
const mergedRuntimeFilterIds = [...props.configuredMandatoryRuntimeFilters, ...nonMandatoryApplied]

const runtimeFilters = useFilters(props.appliedRuntimeFilters, mergedRuntimeFilterIds)
const initialRuntimeFilters = ref<ConfiguredFilters>(
  JSON.parse(JSON.stringify(runtimeFilters.getFilters()))
)
const mandatoryRuntimeFilters = useFilters(undefined, props.configuredMandatoryRuntimeFilters)

// Unfortunate addition as the requirements changed which forces us to completely remount during filter reset
const resetCounter = ref(0)

// Track whether the filter settings sub-window is open
const isFilterSettingsWindowOpen = ref(props.startingWindow === 'filter-settings')
const filterSettingsTab = ref<string | number>('dashboard-filter')

const filterSettingsTabs: {
  id: string
  title: string
}[] = [
  {
    id: 'dashboard-filter',
    title: 'Default filters'
  },
  {
    id: 'required-filter',
    title: 'Runtime filters'
  }
]

const targetFilters = computed(() => {
  if (!isFilterSettingsWindowOpen.value) {
    return runtimeFilters
  }
  switch (filterSettingsTab.value) {
    case 'dashboard-filter':
      return dashboardFilters
    case 'required-filter':
      return mandatoryRuntimeFilters
    default:
      return dashboardFilters
  }
})

const openSettingsWindow = () => {
  filterSettingsTab.value = 'dashboard-filter'
  isFilterSettingsWindowOpen.value = true
}

const handleUpdateRuntimeFiltersMode = (mode: RuntimeFilterMode) => {
  runtimeFiltersMode.value = mode
}

const handleResetRuntimeFilters = () => {
  const activeFilters = [...runtimeFilters.getSelectedFilters()]
  activeFilters.forEach((filterId) => {
    if (!mandatorySet.value.has(filterId)) {
      runtimeFilters.removeFilter(filterId)
    } else {
      runtimeFilters.clearFilter(filterId)
    }
  })
  resetCounter.value++
}

const handleSaveFilterSettings = () => {
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

  isFilterSettingsWindowOpen.value = false
}

const handleCancelFilterSettings = () => {
  // Restore from props
  mandatoryRuntimeFilters.resetThroughSelectedFilters([...props.configuredMandatoryRuntimeFilters])
  dashboardFilters.setFilters(JSON.parse(JSON.stringify(props.configuredDashboardFilters)))
  runtimeFilters.setFilters(JSON.parse(JSON.stringify(initialRuntimeFilters.value)))
  isFilterSettingsWindowOpen.value = false
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
  <div class="db-filter-settings__main-container">
    <div class="db-filter-settings__selection-container">
      <CmkHeading class="db-filter-settings__selection-container-header" type="h1">{{
        _t('Add filter')
      }}</CmkHeading>
      <FilterSelection
        :category-filter="filterCategories.get('host')!"
        :category-definition="CATEGORY_DEFINITIONS.host!"
        :filters="targetFilters"
        class="db-filter-settings__selection-item"
      />
      <FilterSelection
        :category-filter="filterCategories.get('service')!"
        :category-definition="CATEGORY_DEFINITIONS.service!"
        :filters="targetFilters"
        class="db-filter-settings__selection-item"
      />
    </div>
    <div class="db-filter-settings__definition-container">
      <div class="db-filter-settings__header">
        <CmkHeading type="h1">
          {{ isFilterSettingsWindowOpen ? _t('Filter settings') : _t('Runtime filters') }}
        </CmkHeading>
        <button
          class="db-filter-settings__close-button"
          type="button"
          :aria-label="_t('Close filter settings')"
          @click="closeWindow"
        >
          <CmkIcon :aria-label="_t('Clear search')" name="close" size="xxsmall" />
        </button>
      </div>

      <div v-if="!isFilterSettingsWindowOpen" class="db-filter-settings__filter-container">
        <div>
          <CmkHeading type="h3">
            {{ _t('Runtime filters are required to load data.') }}
          </CmkHeading>
          <CmkParagraph>
            {{ _t('Values are temporary and can be overridden by widget filters.') }}
          </CmkParagraph>
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
          :is-built-in="isBuiltIn"
          :reset-key="resetCounter"
          @update:runtime-filters-mode="handleUpdateRuntimeFiltersMode"
          @apply-runtime-filters="applyRuntimeFilters"
          @open-filter-settings="openSettingsWindow"
          @reset-runtime-filters="handleResetRuntimeFilters"
          @close="closeWindow"
        />
      </div>

      <div v-else>
        <div class="db-filter-settings__filter-settings-subwindow-actions">
          <CmkButton variant="primary" @click="handleSaveFilterSettings">
            {{ _t('Save') }}
          </CmkButton>
          <CmkButton
            variant="optional"
            class="db-filter-settings__cancel-button"
            @click="handleCancelFilterSettings"
          >
            <CmkIcon name="cancel" size="xsmall" />
            {{ _t('Cancel') }}
          </CmkButton>
        </div>

        <CmkTabs v-model="filterSettingsTab">
          <template #tabs>
            <CmkTab
              v-for="tab in filterSettingsTabs"
              :id="tab.id"
              :key="tab.id"
              class="cmk-demo-tabs"
            >
              {{ tab.title }}
            </CmkTab>
          </template>
          <template #tab-contents>
            <CmkTabContent id="dashboard-filter">
              <div class="db-filter-settings__filter-container">
                <div>
                  <CmkHeading type="h3">
                    {{ _t('Set filters for all widgets.') }}
                  </CmkHeading>
                  <CmkParagraph>
                    {{ _t('Values can be overridden by runtime or widget filters.') }}
                  </CmkParagraph>
                </div>
                <hr class="db-filter-settings__hr" />

                <FilterCollection
                  :title="_t('Host filters')"
                  :filters="hostDashboardFilters"
                  :get-filter-values="dashboardFilters.getFilterValues"
                  :additional-item-label="_t('Add filter from left panel')"
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
                  :additional-item-label="_t('Add filter from left panel')"
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
              <div class="db-filter-settings__filter-container">
                <div>
                  <CmkHeading type="h3">
                    {{ _t('Set required filters for viewers to enter on load.') }}
                  </CmkHeading>
                  <CmkParagraph>
                    {{ _t('Values are temporary and can be overridden by widget filters.') }}
                  </CmkParagraph>
                </div>
                <hr class="db-filter-settings__hr" />

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
</template>

<style scoped>
.db-filter-settings__main-container {
  background-color: var(--ux-theme-2);
  display: flex;
  width: 100%;
  flex: 1;
  height: 100vh;
  column-gap: 10px;
}

.db-filter-settings__selection-container {
  position: relative;
  height: calc(100% - 2 * var(--dimension-7));
  padding: var(--dimension-7);
  flex: 1.3;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  background-color: var(--slide-in-left-part);
}

.db-filter-settings__selection-container-header {
  margin-bottom: var(--dimension-7);
}

.db-filter-settings__selection-item {
  flex: 1;
  min-height: 0;
}

.db-filter-settings__definition-container {
  background-color: var(--ux-theme-1);
  flex: 2;
  width: 100%;
  height: 100vh;
  padding: var(--dimension-7);
  overflow-y: auto;
}

.db-filter-settings__header {
  margin-bottom: var(--dimension-8);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.db-filter-settings__close-button {
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

.db-filter-settings__filter-container {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-8);
}

.db-filter-settings__filter-settings-subwindow-actions {
  display: flex;
  align-items: center;
  margin: var(--dimension-8) 0;
  gap: var(--dimension-4);
}

.db-filter-settings__cancel-button {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.db-filter-settings__hr {
  width: 100%;
  border: none;
  border-bottom: var(--dimension-1) solid var(--ux-theme-5);
}
</style>
