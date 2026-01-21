<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { nextTick, ref } from 'vue'

import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

import { getSearchUtils } from '@/unified-search/providers/search-utils'
import type {
  FilterOption,
  ProviderOption,
  QueryProvider
} from '@/unified-search/providers/search-utils.types'

import FilterOptionEntry from './FilterOptionEntry.vue'
import { availableFilterOptions, availableProviderOptions } from './QueryOptions'

const { _t } = usei18n()
const searchUtils = getSearchUtils()

const filterOptions = ref<FilterOption[]>(availableFilterOptions)
const vClickOutside = useClickOutside()
function handleFilterSelect(selected: FilterOption): void {
  if (selected.type === 'provider') {
    searchUtils.input.setProviderValue(selected as ProviderOption)
    searchUtils.input.setInputValue('')
  } else {
    void nextTick(() => {
      searchUtils.input.setInputValue(selected.value)
    })
  }

  hideFilterSuggestions()
}

const currentlySelected = ref<number>(-1)
const isFocused = (i: number): boolean =>
  currentlySelected.value === i && searchUtils.input.suggestionsActive.value === true

const shortcutCallbackIds = ref<string[]>([])

shortcutCallbackIds.value.push(searchUtils.shortCuts.onEscape(hideFilterSuggestions))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))

function toggleDown() {
  calcCurrentlySelected(+1)
}

function toggleUp() {
  calcCurrentlySelected(-1)
}

function calcCurrentlySelected(d: number, set: boolean = false) {
  if (searchUtils.input.suggestionsActive.value === true) {
    if (set) {
      currentlySelected.value = d
    } else {
      currentlySelected.value += d
    }

    if (currentlySelected.value === -1 || currentlySelected.value > getFilterOptions().length - 1) {
      currentlySelected.value = -1
      searchUtils.input?.setFocus()
      return
    }

    if (currentlySelected.value < 0) {
      currentlySelected.value += getFilterOptions().length + 1
      return
    }
  }
}

searchUtils.input.onSetInputValue((input?: string) => {
  if (typeof input === 'string') {
    if (input.indexOf('/') === 0) {
      void showFilterSuggestions()
    } else {
      void hideFilterSuggestions()
    }
  }
})

async function showFilterSuggestions() {
  searchUtils.input.suggestionsActive.value = true
}

searchUtils.input.onHideSuggestions(hideFilterSuggestions)

function hideFilterSuggestions() {
  if (searchUtils.input.suggestionsActive.value === true) {
    searchUtils.input.suggestionsActive.value = false

    if (searchUtils.query.input.value.indexOf('/') === 0) {
      searchUtils.input.setInputValue('')
      searchUtils.input.setFocus()
      currentlySelected.value = -1
    }
  }
}

function getFilterOptions(): FilterOption[] {
  return filterOptions.value.filter((fo) => {
    return (
      searchUtils.query.input.value.indexOf(fo.value) === -1 &&
      searchUtils.query.filters.value.findIndex(
        (f) => f.type === fo.type && f.value === fo.value
      ) === -1 &&
      (fo.title.toLowerCase().indexOf(searchUtils.query.input.value.substring(1).toLowerCase()) >=
        0 ||
        fo.value.toLowerCase().indexOf(searchUtils.query.input.value.substring(1).toLowerCase()) >=
          0) &&
      (fo.type === 'inline' &&
        searchUtils.query.filters.value.findIndex(
          (f) => fo.notAvailableFor && fo.notAvailableFor?.indexOf(f.value as QueryProvider) >= 0
        )) === -1
    )
  })
}

const deletePressedRef = ref<number>()
searchUtils.input.onEmptyBackspace(() => {
  if (deletePressedRef.value && Date.now() - deletePressedRef.value < 1000) {
    searchUtils.input.setProviderValue(availableProviderOptions[0])
    return
  }

  deletePressedRef.value = Date.now()
})
</script>

<template>
  <div
    v-if="searchUtils.input.suggestionsActive.value === true"
    v-click-outside="hideFilterSuggestions"
    class="unified-search-filters__suggestions"
  >
    <ul ref="unified-search-filters__suggestions" class="unified-search-filters__suggestions-list">
      <FilterOptionEntry
        v-for="(opt, idx) in getFilterOptions()"
        :key="opt.type.concat(opt.value)"
        :class="opt.type"
        :focus="isFocused(idx)"
        :idx="idx"
        :option="opt"
        @click.stop="() => handleFilterSelect(opt)"
        @keydown.enter.stop="() => handleFilterSelect(opt)"
      ></FilterOptionEntry>
    </ul>
    <CmkAlertBox
      v-if="getFilterOptions().length === 0"
      variant="info"
      class="unified-search-filters__suggestions-info not-found"
    >
      {{ _t('No filters can be applied to your current search query.') }}
    </CmkAlertBox>
    <CmkAlertBox variant="info" class="unified-search-filters__suggestions-info">
      {{
        _t(
          'Search with regular expressions for menu entries, hosts, services or host and service groups.'
        )
      }}
      <br />

      {{ _t("Note that for simplicity '*' will be substituted with '.*'.") }}
    </CmkAlertBox>
  </div>
</template>

<style scoped>
.unified-search-filters__suggestions {
  position: absolute;
  top: 30px;
  left: var(--spacing-half);
  width: calc(100% - 24px);
  padding: 0;
  background: var(--default-form-element-bg-color);
  height: auto;
  border-bottom-left-radius: var(--border-radius-half);
  border-bottom-right-radius: var(--border-radius-half);
  z-index: +1;
}

.unified-search-filters__suggestions-list {
  position: relative;
  border: 1px solid var(--ux-theme-6);
  padding: 0;
  margin: 0;
}

.unified-search-filters__suggestions-info {
  border: 1px solid var(--ux-theme-6);
  border-top: 0;
  margin: 0;
  font-style: italic;
  color: var(--dropdown-chevron-indicator-color);
  border-top-left-radius: 0;
  border-top-right-radius: 0;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.not-found {
    border-radius: 0;
  }
}
</style>
