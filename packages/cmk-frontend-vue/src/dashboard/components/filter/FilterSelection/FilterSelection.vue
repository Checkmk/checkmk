<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { Filters } from '../composables/useFilters.ts'
import type { FilterType } from '../types.ts'
import FilterSelectionActiveIcon from './FilterSelectionActiveIcon.vue'
import FilterSelectionSearch from './FilterSelectionSearch.vue'
import type { FlatFilter } from './types'
import { type CategoryDefinition, type FilterGroup, buildProcessedCategories } from './utils'

interface Props {
  categoryFilter: FilterType[]
  categoryDefinition: CategoryDefinition
  filters: Filters
}

interface ProcessedFilterCategory {
  name: string
  title: string
  entries: (FilterType | FilterGroup)[]
}

const { _t } = usei18n()
const props = defineProps<Props>()

const collapsibleStates = ref<Record<string, boolean>>({})
const processedCategory = ref<ProcessedFilterCategory | null>(null)

const allFilters = computed((): FlatFilter[] => {
  if (!processedCategory.value) {
    return []
  }

  const filters: FlatFilter[] = []

  processedCategory.value.entries.forEach((entry) => {
    if (entry.type === 'filter') {
      filters.push({
        id: entry.id,
        title: entry.title
      })
    } else if (entry.type === 'group') {
      entry.entries.forEach((filter) => {
        filters.push({
          id: filter.id,
          title: filter.title,
          groupName: entry.name
        })
      })
    }
  })

  return filters
})

const totalFilterCount = computed(() => {
  return props.categoryFilter.length
})

const getGroupFilterCount = (group: FilterGroup) => {
  const selectedCount = group.entries.filter((filter) =>
    props.filters.isFilterActive(filter.id)
  ).length
  const totalCount = group.entries.length
  return { selectedCount, totalCount }
}

const isGroupActive = (group: FilterGroup) => {
  return getGroupFilterCount(group).selectedCount > 0
}

const getGroupTitle = (group: FilterGroup) => {
  return group.name
}

const getGroupSideTitle = (group: FilterGroup) => {
  const { selectedCount, totalCount } = getGroupFilterCount(group)
  return `(${selectedCount} of ${totalCount})`
}

const groupStates = computed(() => {
  if (!processedCategory.value) {
    return { allExpanded: false, allCollapsed: true }
  }

  const groupKeys = processedCategory.value.entries
    .filter((entry) => entry.type === 'group')
    .map((entry) => `${processedCategory.value!.name}-${entry.name}`)

  if (groupKeys.length === 0) {
    return { allExpanded: false, allCollapsed: true }
  }

  const expandedCount = groupKeys.filter((key) => collapsibleStates.value[key]).length

  return {
    allExpanded: expandedCount === groupKeys.length,
    allCollapsed: expandedCount === 0
  }
})

function initializeCategory() {
  const categoryMap = new Map()
  categoryMap.set(props.categoryDefinition.name, props.categoryFilter)

  const processedCategories = buildProcessedCategories([props.categoryDefinition], categoryMap)

  processedCategory.value = processedCategories[0] || null

  collapsibleStates.value = {}
  if (processedCategory.value) {
    processedCategory.value.entries.forEach((entry) => {
      if (entry.type === 'group') {
        collapsibleStates.value[`${processedCategory.value!.name}-${entry.name}`] = false
      }
    })
  }
}

function toggleCollapsible(groupName: string) {
  if (!processedCategory.value) {
    return
  }
  const key = `${processedCategory.value.name}-${groupName}`
  collapsibleStates.value[key] = !collapsibleStates.value[key]
}

function selectFilterFromSearch(filterId: string) {
  props.filters.toggleFilter(filterId)
}

function expandAllGroups() {
  if (!processedCategory.value) {
    return
  }
  processedCategory.value.entries.forEach((entry) => {
    if (entry.type === 'group') {
      collapsibleStates.value[`${processedCategory.value!.name}-${entry.name}`] = true
    }
  })
}

function collapseAllGroups() {
  if (!processedCategory.value) {
    return
  }
  processedCategory.value.entries.forEach((entry) => {
    if (entry.type === 'group') {
      collapsibleStates.value[`${processedCategory.value!.name}-${entry.name}`] = false
    }
  })
}

onMounted(() => {
  initializeCategory()
})
</script>

<template>
  <div class="db-filter-selection__main-container">
    <template v-if="processedCategory">
      <div class="filter-menu__sticky-header">
        <CmkHeading type="h2">
          {{ `${untranslated(processedCategory.title)} ${_t('filter')}` }}
        </CmkHeading>

        <FilterSelectionSearch
          :all-filters="allFilters"
          :active-filters="filters.activeFilters.value"
          class="db-filter-selection__search-container"
          @select-filter="selectFilterFromSearch"
        />

        <div v-if="Object.keys(collapsibleStates).length > 0" class="filter-menu__controls-row">
          <div class="filter-menu__expand-controls">
            <button
              v-if="!groupStates.allExpanded"
              class="filter-menu__control-btn"
              @click="expandAllGroups"
            >
              {{ _t('Expand all') }}
            </button>
            <button
              v-if="!groupStates.allCollapsed"
              class="filter-menu__control-btn"
              @click="collapseAllGroups"
            >
              {{ _t('Collapse all') }}
            </button>
          </div>
          <div class="filter-menu__selection-summary">
            {{
              `${filters.selectedFilterCount.value} ${_t('of')} ${totalFilterCount} ${_t('selected')}`
            }}
          </div>
        </div>
      </div>

      <div class="db-filter-selection__scroll-container">
        <CmkScrollContainer type="outer">
          <div class="filter-menu__entries">
            <template
              v-for="entry in processedCategory.entries"
              :key="`${processedCategory.name}-${entry.type === 'group' ? entry.name : entry.id}`"
            >
              <div
                v-if="entry.type === 'filter'"
                class="filter-menu__filter-item"
                @click="filters.toggleFilter(entry.id)"
              >
                <FilterSelectionActiveIcon :is-active="filters.isFilterActive(entry.id)" />
                <div class="filter-menu__filter-title">
                  <CmkLabel>{{ entry.title }}</CmkLabel>
                </div>
              </div>

              <div v-else-if="entry.type === 'group'" class="filter-menu__group">
                <div class="filter-menu__group-header">
                  <FilterSelectionActiveIcon :is-active="isGroupActive(entry)" />
                  <CmkCollapsibleTitle
                    :title="untranslated(getGroupTitle(entry))"
                    :side-title="untranslated(getGroupSideTitle(entry))"
                    :open="collapsibleStates[`${processedCategory.name}-${entry.name}`] ?? false"
                    @toggle-open="toggleCollapsible(entry.name)"
                  />
                </div>
                <CmkCollapsible
                  :open="collapsibleStates[`${processedCategory.name}-${entry.name}`] ?? false"
                >
                  <div class="filter-menu__group-content">
                    <div
                      v-for="filterItem in entry.entries"
                      :key="filterItem.id"
                      class="filter-menu__filter-item filter-menu__filter-item--grouped"
                      @click="filters.toggleFilter(filterItem.id)"
                    >
                      <FilterSelectionActiveIcon
                        :is-active="filters.isFilterActive(filterItem.id)"
                      />
                      <span class="filter-menu__filter-title">{{ filterItem.title }}</span>
                    </div>
                  </div>
                </CmkCollapsible>
              </div>
            </template>
          </div>
        </CmkScrollContainer>
      </div>
    </template>

    <CmkParagraph v-else>{{ _t('No filter category available') }}</CmkParagraph>
  </div>
</template>

<style scoped>
.db-filter-selection__main-container {
  display: flex;
  flex-direction: column;
}

.db-filter-selection__scroll-container {
  min-height: 0;
  border-image: linear-gradient(to right, var(--color-digital-green-0), var(--color-mid-grey-60)) 1;
  border-width: 0 0 1px;
  border-style: solid;
}

.db-filter-selection__search-container {
  position: relative;
  margin-top: var(--dimension-4);
  margin-bottom: var(--dimension-6);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__sticky-header {
  position: sticky;
  top: 0;
  z-index: 10;
  padding-bottom: var(--dimension-4);
  margin-bottom: var(--dimension-4);
  border-bottom: 1px solid transparent;
  background-color: var(--slide-in-left-part);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__selection-summary {
  color: var(--font-color);
  font-size: var(--font-size-normal);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__controls-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__control-btn {
  font-size: var(--font-size-normal);
  background: none;
  color: var(--font-color);
  border: none;
  cursor: pointer;
  text-decoration: underline;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__entries {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  min-height: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__filter-item {
  display: flex;
  align-items: center;
  padding: var(--dimension-3) var(--dimension-4);
  cursor: pointer;
  border-radius: var(--dimension-3);
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__filter-item--grouped {
  margin-left: var(--dimension-6);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__filter-title {
  color: var(--font-color);
  flex: 1;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__group {
  overflow: hidden;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__group-header {
  display: flex;
  align-items: center;
  padding: 0 var(--dimension-4);
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__group-header .cmk-collapsible-title {
  flex: 1;
  position: static;
  margin: 0;
  padding: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__group-content {
  padding: var(--dimension-4);
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}
</style>
