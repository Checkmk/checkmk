<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import FilterSelectionSearchBox from './FilterSelectionSearchBox.vue'
import type { FlatFilter } from './types'

interface Props {
  allFilters: FlatFilter[]
  activeFilters: string[]
}
const props = defineProps<Props>()
const emit = defineEmits<{
  'select-filter': [filterId: string]
}>()

const { _t } = usei18n()
const containerRef = useTemplateRef('containerRef')
const searchTerm = ref<string>('')

const searchRegex = computed(() => {
  const sanitized = searchTerm.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').trimEnd()
  return new RegExp(sanitized, 'i')
})

const highlightRegex = computed(() => {
  // we want to highlight all matches, so we add the global flag
  // we can't use the global flag for searching, because `test` then changes its state
  return new RegExp(searchRegex.value, 'ig')
})

const searchResults = computed(() => {
  if (!searchTerm.value.trim()) {
    return []
  }

  return props.allFilters.filter((filter) => searchRegex.value.test(filter.title))
})

const showSearchDropdown = computed(() => searchTerm.value.trim().length > 0)

function selectFilterFromDropdown(filterId: string) {
  searchTerm.value = ''
  emit('select-filter', filterId)
}

function handleClickOutside(event: Event) {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    searchTerm.value = ''
  }
}

function formatFilterDisplay(filter: FlatFilter) {
  const title = filter.title.replace(
    highlightRegex.value,
    `<span class="db-filter-selection-search__result-highlight">$&</span>`
  )
  if (filter.groupName) {
    return _t('%{filterName} in %{filterGroup}', {
      filterName: title,
      filterGroup: filter.groupName
    })
  }
  return title
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="containerRef">
    <FilterSelectionSearchBox v-model="searchTerm" />

    <div v-if="showSearchDropdown" class="db-filter-selection-search__dropdown">
      <CmkParagraph
        v-if="searchResults.length === 0"
        class="db-filter-selection-search__no-results"
      >
        {{ _t('No filters found matching: %{search}', { search: searchTerm }) }}
      </CmkParagraph>
      <template v-else>
        <CmkHeading type="h4" class="db-filter-selection-search__results-header">
          {{ `${_t('Results')} (${searchResults.length})` }}
        </CmkHeading>
        <CmkScrollContainer
          type="outer"
          max-height="300px"
          class="db-filter-selection-search__results-container"
        >
          <div
            v-for="filter in searchResults"
            :key="filter.id"
            class="db-filter-selection-search__result"
            @click="selectFilterFromDropdown(filter.id)"
          >
            <div class="db-filter-selection-search__result-content">
              <span
                class="db-filter-selection-search__result-checkmark"
                :class="{
                  'db-filter-selection-search__result-checkmark--active': activeFilters.includes(
                    filter.id
                  )
                }"
              ></span>
              <CmkParagraph>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span v-html="formatFilterDisplay(filter)" />
              </CmkParagraph>
            </div>
          </div>
        </CmkScrollContainer>
      </template>
    </div>
  </div>
</template>

<style scoped>
.db-filter-selection-search__dropdown {
  position: absolute;
  left: 0;
  right: 0;
  z-index: +1;
  background: var(--slide-in-left-part);
  border: 1px solid var(--default-form-element-border-color);
  border-top: none;
  border-radius: 0 0 var(--border-radius) var(--border-radius);
}

.db-filter-selection-search__no-results {
  padding: var(--dimension-4);
}

.db-filter-selection-search__results-header {
  padding: var(--dimension-4);
  background: var(--slide-in-left-part);
}

.db-filter-selection-search__results-container {
  margin: 0 var(--dimension-4);
}

.db-filter-selection-search__result {
  color: var(--font-color);
  cursor: pointer;
  padding: var(--dimension-5) var(--dimension-4);

  &:nth-child(even) {
    background: var(--ux-theme-3);
  }

  &:nth-child(odd) {
    background: var(--ux-theme-2);
  }

  &:hover {
    background: var(--ux-theme-5);
  }
}

.db-filter-selection-search__result-content {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.db-filter-selection-search__result-checkmark {
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

.db-filter-selection-search__result-checkmark--active {
  background-image: url('~cmk-frontend/themes/facelift/images/icon_checkmark.svg');
  border-radius: 100%;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.db-filter-selection-search__result-highlight) {
  color: var(--success);
}
</style>
