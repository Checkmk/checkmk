<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkIcon from '@/components/CmkIcon'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import type { Filters } from '../composables/useFilters.ts'
import type { FilterType } from '../types.ts'
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

interface FlatFilter {
  id: string
  title: string
  groupName?: string
}

const { _t } = usei18n()
const props = defineProps<Props>()

const collapsibleStates = ref<Record<string, boolean>>({})
const searchTerm = ref('')
const processedCategory = ref<ProcessedFilterCategory | null>(null)
const showSearchDropdown = ref(false)
const searchDropdownRef = ref<HTMLElement | null>(null)

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

const searchResults = computed(() => {
  if (!searchTerm.value.trim()) {
    return []
  }

  const lowerSearchTerm = searchTerm.value.toLowerCase()
  return allFilters.value.filter((filter) => filter.title.toLowerCase().includes(lowerSearchTerm))
})

const isSearching = computed(() => searchTerm.value.trim().length > 0)

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

function clearSearch() {
  searchTerm.value = ''
  showSearchDropdown.value = false
}

function handleSearchInput() {
  showSearchDropdown.value = isSearching.value
}

function selectFilterFromDropdown(filterId: string) {
  props.filters.toggleFilter(filterId)
  clearSearch()
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

function handleClickOutside(event: Event) {
  if (searchDropdownRef.value && !searchDropdownRef.value.contains(event.target as Node)) {
    showSearchDropdown.value = false
  }
}

onMounted(() => {
  initializeCategory()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="db-filter-selection__main-container">
    <div v-if="processedCategory" class="filter-menu">
      <div class="filter-menu__sticky-header">
        <h3 class="filter-menu__main-title">
          {{ `${untranslated(processedCategory.title)} ${_t('filter')}` }}
        </h3>

        <div ref="searchDropdownRef" class="filter-menu__search-container">
          <input
            v-model="searchTerm"
            type="text"
            :placeholder="_t('Search Filter')"
            class="filter-menu__search-input"
            @input="handleSearchInput"
          />
          <button
            v-if="searchTerm"
            class="filter-menu__search-clear"
            :title="_t('Clear search')"
            @click="clearSearch"
          >
            <CmkIcon :aria-label="_t('Clear search')" name="close" size="xxsmall" />
          </button>

          <div v-if="showSearchDropdown" class="filter-menu__search-dropdown">
            <div v-if="searchResults.length === 0" class="filter-menu__search-no-results">
              <span>
                {{ _t('No filters found matching') }}
              </span>
              <span>
                {{ searchTerm }}
              </span>
            </div>
            <template v-else>
              <div class="filter-menu__search-result-header">
                <span class="filter-menu__search-result-count">
                  {{ `${_t('Result')} (${searchResults.length})` }}
                </span>
              </div>
              <div class="filter-menu__search-results-container">
                <div
                  v-for="filter in searchResults"
                  :key="filter.id"
                  class="filter-menu__search-result"
                  :class="{
                    'filter-menu__search-result--active': filters.isFilterActive(filter.id)
                  }"
                  @click="selectFilterFromDropdown(filter.id)"
                >
                  <div class="filter-menu__search-result-content">
                    <span
                      class="filter-menu__filter-checkmark"
                      :class="{
                        'filter-menu__filter-checkmark--active': filters.isFilterActive(filter.id)
                      }"
                    ></span>
                    <div class="filter-menu__search-result-text">
                      <span class="filter-menu__search-result-title">{{ filter.title }}</span>
                      <span v-if="filter.groupName" class="filter-menu__search-result-group">
                        {{ `${_t('in')} ${untranslated(filter.groupName)}` }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

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

      <CmkScrollContainer
        :max-height="`calc(100% - 130px)`"
        :height="`calc(100% - 130px)`"
        type="outer"
        class="db-filter-selection__scroll-container"
      >
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
              <span
                class="filter-menu__filter-checkmark"
                :class="{
                  'filter-menu__filter-checkmark--active': filters.isFilterActive(entry.id)
                }"
              ></span>
              <div class="filter-menu__filter-title">
                <CmkLabel>{{ entry.title }}</CmkLabel>
              </div>
            </div>

            <div v-else-if="entry.type === 'group'" class="filter-menu__group">
              <div class="filter-menu__group-header">
                <span
                  class="filter-menu__filter-checkmark"
                  :class="{
                    'filter-menu__filter-checkmark--active': isGroupActive(entry)
                  }"
                ></span>
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
                    :class="{
                      'filter-menu__filter-item--active': filters.isFilterActive(filterItem.id)
                    }"
                    @click="filters.toggleFilter(filterItem.id)"
                  >
                    <span
                      class="filter-menu__filter-checkmark"
                      :class="{
                        'filter-menu__filter-checkmark--active': filters.isFilterActive(
                          filterItem.id
                        )
                      }"
                    ></span>
                    <span class="filter-menu__filter-title">{{ filterItem.title }}</span>
                  </div>
                </div>
              </CmkCollapsible>
            </div>
          </template>
        </div>
      </CmkScrollContainer>
    </div>

    <div v-else class="filter-menu__empty">{{ _t('No filter category available') }}</div>
  </div>
</template>

<style scoped>
.db-filter-selection__main-container {
  margin: var(--dimension-9) var(--dimension-7);
}

.db-filter-selection__scroll-container {
  border-image: linear-gradient(to right, var(--color-digital-green-0), var(--color-mid-grey-60)) 1;
  border-width: 0 0 1px;
  border-style: solid;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu::-webkit-scrollbar {
  display: none;
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
.filter-menu__main-title {
  margin: 0 0 var(--dimension-5) 0;
  font-size: var(--font-size-xlarge);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-container {
  position: relative;
  margin-bottom: var(--dimension-6);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-input {
  width: 100%;
  padding: var(--dimension-6) var(--dimension-5);
  padding-right: var(--dimension-10);
  border: 1px solid var(--ux-theme-10);
  border-radius: var(--dimension-1);
  font-size: var(--font-size-large);
  background-color: var(--slide-in-left-part);
  color: var(--font-color);
  box-sizing: border-box;
  min-width: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 var(--dimension-2) var(--font-color);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-clear {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 20;
  background: var(--ux-theme-1);
  max-height: 300px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--ux-theme-10);
  border-top: none;
  border-radius: 0 0 var(--dimension-2) var(--dimension-2);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-result-header {
  position: sticky;
  top: 0;
  z-index: 21;
  padding: var(--dimension-4);
  background: var(--ux-theme-1);
  border-bottom: 1px solid var(--ux-theme-3);
  margin-bottom: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-result-count {
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-results-container {
  flex: 1;
  padding: 0 8px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-results-container::-webkit-scrollbar {
  display: none;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-no-results {
  padding: var(--dimension-4);
  color: var(--font-color);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-result {
  color: var(--font-color);
  cursor: pointer;
  transition: all 0.2s ease;
  padding: var(--dimension-5) var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-result:nth-child(even) {
  background: var(--ux-theme-3);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-result:nth-child(odd) {
  background: var(--ux-theme-2);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-result:last-child {
  border-bottom: none;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__search-result-content {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
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
.filter-menu__filter-checkmark {
  width: var(--dimension-6);
  height: var(--dimension-6);
  min-width: var(--dimension-6);
  min-height: var(--dimension-6);
  display: inline-block;
  background-repeat: no-repeat;
  background-position: center center;
  background-size: var(--dimension-6) var(--dimension-6);
  flex-shrink: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-menu__filter-checkmark--active {
  background-image: url('~cmk-frontend/themes/facelift/images/icon_checkmark.svg');
  border-radius: 100%;
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
