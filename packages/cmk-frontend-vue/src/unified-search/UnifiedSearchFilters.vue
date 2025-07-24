<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { getSearchUtils, type FilterOption } from './providers/search-utils'
import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'
import CmkAlertBox from '@/components/CmkAlertBox.vue'
import FilterOptionEntry from './FilterOptionEntry.vue'

const { t } = usei18n('unified-search-app')
const searchUtils = getSearchUtils()

const filterOptions = ref<FilterOption[]>([
  { type: 'provider', value: 'setup', title: 'Only search in setup' },
  { type: 'provider', value: 'monitoring', title: 'Only search in monitoring' },
  { type: 'inline', value: 'h:', title: 'Host', notAvailableFor: ['setup'] },
  { type: 'inline', value: 's:', title: 'Service', notAvailableFor: ['setup'] },
  { type: 'inline', value: 'hg:', title: 'Host group', notAvailableFor: ['setup'] },
  { type: 'inline', value: 'sg:', title: 'Service group', notAvailableFor: ['setup'] },
  { type: 'inline', value: 'ad:', title: 'Address', notAvailableFor: ['setup'] },
  { type: 'inline', value: 'al:', title: 'Alias', notAvailableFor: ['setup'] },
  { type: 'inline', value: 'tg:', title: 'Host tag', notAvailableFor: ['setup'] },
  {
    type: 'inline',
    value: 'hl:',
    title: 'Host label (e.g. hl: cmk/os_family:linux)',
    notAvailableFor: ['setup']
  },
  {
    type: 'inline',
    value: 'sl:',
    title: 'Service label (e.g. sl: cmk/os_family:linux)',
    notAvailableFor: ['setup']
  },
  {
    type: 'inline',
    value: 'st:',
    title: 'Service state (e.g. st: crit [ok|warn|crit|unkn|pend])',
    notAvailableFor: ['setup']
  }
])
const vClickOutside = useClickOutside()
function handleFilterSelect(selected: FilterOption): void {
  if (selected.type === 'provider') {
    addFilter(selected)
    searchUtils.input.setInputValue('')
  } else {
    console.log(selected.value)
    void nextTick(() => {
      searchUtils.input.setInputValue(selected.value)
    })
  }

  hideFilterSuggestions()
}

const currentlySelected = ref<number>(-1)
const isFocused = (i: number): boolean =>
  currentlySelected.value === i && searchUtils.input.suggestionsActive.value === true

const scCallbackIds = ref<string[]>([])

scCallbackIds.value.push(searchUtils.shortCuts.onEscape(hideFilterSuggestions))
scCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
scCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))

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

function addFilter(filterOption: FilterOption) {
  const filters = searchUtils.query.filters.value.slice(0)
  if (
    filters.findIndex((f) => f.type === filterOption.type && f.value === filterOption.value) === -1
  ) {
    filters.push(filterOption)
    searchUtils.input.setFilterValue(filters)
  }
}

function popFilter() {
  const filters = searchUtils.query.filters.value.slice(0)

  filters.pop()
  searchUtils.input.setFilterValue(filters)
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

function hideFilterSuggestions() {
  if (searchUtils.input.suggestionsActive.value === true) {
    searchUtils.input.suggestionsActive.value = false

    searchUtils.input.setInputValue('')
    searchUtils.input.setFocus()
    currentlySelected.value = -1
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
      ((fo.type === 'inline' &&
        searchUtils.query.filters.value.findIndex(
          (f) => fo.notAvailableFor && fo.notAvailableFor?.indexOf(f.value) >= 0
        )) === -1 ||
        (fo.type === 'provider' &&
          searchUtils.query.filters.value.findIndex((f) => f.type === 'provider') === -1))
    )
  })
}

const deletePressedRef = ref<number>()
searchUtils.input.onEmptyBackspace(() => {
  if (deletePressedRef.value && Date.now() - deletePressedRef.value < 1000) {
    popFilter()
    return
  }

  deletePressedRef.value = Date.now()
})
</script>

<template>
  <div
    v-if="searchUtils.input.suggestionsActive.value === true"
    v-click-outside="hideFilterSuggestions"
    class="unified-search-filter-suggestions"
  >
    <ul ref="unified-search-filter-suggestions" class="unified-search-filter-suggestions-list">
      <FilterOptionEntry
        v-for="(opt, idx) in getFilterOptions()"
        :key="opt.type.concat(opt.value)"
        :class="opt.type"
        :focus="isFocused(idx)"
        :idx="idx"
        :option="opt"
        @click.stop="() => handleFilterSelect(opt)"
        @keypres.enter.stop="() => handleFilterSelect(opt)"
      ></FilterOptionEntry>
    </ul>
    <CmkAlertBox
      v-if="getFilterOptions().length === 0"
      variant="info"
      class="unified-search-filter-suggestions-info not-found"
    >
      {{
        t('no-matching-suggestions-fond', 'No filters can be applied to your current search query.')
      }}
    </CmkAlertBox>
    <CmkAlertBox variant="info" class="unified-search-filter-suggestions-info">
      {{
        t(
          'sarch-with-regex',
          'Search with regular expressions for menu entries, hosts, services or host and service groups.'
        )
      }}
      <br />

      {{ t('asterrisk-sub', "Note that for simplicity '*' will be substituted with '.*'.") }}
    </CmkAlertBox>
  </div>
</template>

<style scoped>
.unified-search-filter-suggestions {
  position: absolute;
  top: 30px;
  left: var(--spacing-half);
  width: calc(100% - 24px);
  padding: 0;
  background: var(--default-form-element-bg-color);
  height: auto;
  border-bottom-left-radius: var(--border-radius-half);
  border-bottom-right-radius: var(--border-radius-half);
}

.unified-search-filter-suggestions-list {
  position: relative;
  border: 1px solid var(--ux-theme-6);
  padding: 0;
  margin: 0;
}

.unified-search-filter-suggestions-info {
  border: 1px solid var(--ux-theme-6);
  border-top: 0;
  margin: 0;
  font-style: italic;
  color: var(--help-text-font-color);
  border-top-left-radius: 0;
  border-top-right-radius: 0;

  &.not-found {
    border-radius: 0;
  }
}
</style>
