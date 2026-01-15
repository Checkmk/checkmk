<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import { staticAssertNever } from '@/lib/typeUtils'

import CmkIcon from '@/components/CmkIcon'
import CmkKeyboardKey from '@/components/CmkKeyboardKey.vue'

import { HistoryEntry } from '@/unified-search/lib/searchHistory'
import { getSearchUtils } from '@/unified-search/providers/search-utils'
import type { FilterOption } from '@/unified-search/providers/search-utils.types'

import UnifiedSearchFilters from './UnifiedSearchFilters.vue'
import UnifiedSearchOperatorSelect from './UnifiedSearchOperatorSelect.vue'
import UnifiedSearchProviderSelect from './UnifiedSearchProviderSelect.vue'

interface CmkWindow extends Window {
  main: Window
}

const { _t } = usei18n()

const searchUtils = getSearchUtils()
const searchInput = useTemplateRef('unified-search-input')
searchUtils.onResetSearch(() => {
  setTimeout(() => {
    searchUtils.query.filters.value = []
    searchUtils.query.input.value = ''
    setFocus()
  })
})

searchUtils.input?.onSetFocus(setFocus)
function setFocus() {
  if (searchInput.value) {
    if (document.activeElement !== searchInput.value) {
      searchInput.value.focus()
      searchInput.value.selectionStart = searchInput.value.selectionEnd =
        searchUtils.query.input.value.length
    }
  }
}

searchUtils.input?.onSetBlur(() => {
  searchInput.value?.blur()
})

searchUtils.input?.onSetInputValue((input?: string, noSet?: boolean) => {
  if (!noSet) {
    if (typeof input === 'string') {
      searchUtils.query.input.value = input
    } else {
      searchUtils.query.input.value = ''
    }
  }
  setQuery()
})

searchUtils.input?.onSetFilterValue((fo?: FilterOption[], noSet?: boolean) => {
  if (!noSet) {
    if (Array.isArray(fo)) {
      searchUtils.query.filters.value = fo
    } else {
      searchUtils.query.filters.value = []
    }
  }
  setQuery()
})

function setQuery() {
  searchUtils.input.setQuery(searchUtils.query.toQueryLike())
}

function onInput(e: Event) {
  searchUtils.input.setInputValue((e.target as HTMLInputElement).value)
}

function checkEmptyBackspace(e: KeyboardEvent) {
  if (e.key === 'Backspace') {
    if (searchUtils.query.input.value === '') {
      searchUtils.input.emptyBackspace()
    }
  }
}

function onInputEnter() {
  if (isMonitoringSearch()) {
    if (searchUtils.query.input.value.length > 0) {
      const url = 'search_open.py?q='.concat(searchUtils.query.input.value.replace(/^\//, ''))
      searchUtils.history?.add(
        new HistoryEntry(searchUtils.query.toQueryLike(), {
          title: searchUtils.query.input.value,
          target: { url },
          topic: 'Host/service search',
          provider: 'monitoring',
          context: '',
          icon: { type: 'default_icon', id: 'main-search' }
        })
      )
      ;(top!.frames as CmkWindow).main.location.href = url

      searchUtils.closeSearch()
      searchUtils.resetSearch()
    }
  }
}

function isMonitoringSearch(): boolean {
  return ['all', 'monitoring'].indexOf(searchUtils.query.provider.value) >= 0
}

const getSearchInputPlaceholder = computed(() => {
  switch (searchUtils.query.provider.value) {
    case 'all':
      return _t("Search across Checkmk – Type '/' for search operators")
    case 'monitoring':
      return _t("Search in monitoring – Type '/' for search operators")
    case 'customize':
      return _t('Search in customize')
    case 'setup':
      return _t('Search in setup')
    default:
      staticAssertNever(searchUtils.query.provider.value)
      return ''
  }
})
</script>

<template>
  <div class="unified-search-header">
    <div class="unified-search-input-panel">
      <div class="unified-search-input-wrapper" @click="searchUtils.input.setFocus">
        <div class="unified-search-input-tag-root">
          <UnifiedSearchProviderSelect></UnifiedSearchProviderSelect>
          <CmkIcon class="unified-search-icon" name="main-search" size="medium"></CmkIcon>
          <input
            id="unified-search-input"
            ref="unified-search-input"
            v-model="searchUtils.query.input.value"
            role="search"
            class="unified-search-input"
            :aria-label="getSearchInputPlaceholder"
            :placeholder="getSearchInputPlaceholder"
            autocomplete="one-time-code"
            @input="onInput"
            @keydown.delete="checkEmptyBackspace"
            @keydown.enter="onInputEnter"
          />
          <UnifiedSearchFilters v-if="isMonitoringSearch()"></UnifiedSearchFilters>
        </div>

        <CmkIcon
          v-if="
            searchUtils.query.input.value.length > 0 || searchUtils.query.filters.value.length > 0
          "
          class="unified-search-reset"
          name="close"
          size="small"
          @click.stop="searchUtils.resetSearch"
        ></CmkIcon>

        <div
          v-if="isMonitoringSearch() && searchUtils.query.input.value.length > 0"
          class="unified-search-info-item"
        >
          <span>{{ _t('Press') }}</span>
          <CmkKeyboardKey keyboard-key="enter" size="small"></CmkKeyboardKey>
          <span>{{ _t('to trigger host/service search') }}</span>
        </div>
      </div>

      <UnifiedSearchOperatorSelect :disabled="!isMonitoringSearch()"> </UnifiedSearchOperatorSelect>
    </div>
  </div>
</template>

<style scoped>
.unified-search-header {
  height: 75px;
  min-height: 75px !important;
  z-index: +1;
  width: calc(100% - 2 * var(--spacing-double));
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding: 0 var(--spacing-double);
  border-top: 1px solid var(--default-nav-border-color);
  border-bottom: 1px solid var(--default-nav-border-color);
}

/* stylelint-disable checkmk/vue-bem-naming-convention */

.unified-search-input-panel {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}

.unified-search-info-panel {
  display: flex;
  flex-direction: row;
  justify-content: start;
  height: 30px;
}

.unified-search-input-wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 70%;
  position: relative;
  flex: 5;
  margin-right: var(--dimension-4);
}

.unified-search-input-tag-root {
  background-color: var(--default-form-element-bg-color);
  box-shadow: none;
  filter: none;
  padding: 0 35px 0 0;
  width: 100%;
  border-radius: var(--border-radius);
  border: 1px solid var(--default-form-element-border-color);
  line-height: 15px;
  height: 27px;
  position: relative;
  display: flex;
  align-items: center;

  &:focus-within {
    border: 1px solid var(--success);
  }
}

.unified-search-input-tag {
  display: inline-flex;
  align-items: center;
  background: var(--color-yellow-80);
  border-radius: var(--border-radius);
  height: 20px;
  padding: 0 var(--spacing-half);
  margin-right: var(--spacing-half);

  .unified-search-input-tag-dismiss {
    background: transparent;
    border: 0;
    margin: 0 0 0 var(--spacing-half);
    height: 16px;
    max-width: 16px;
    overflow: hidden;
    border-radius: var(--border-radius);
    padding: 0;
    width: 16px;
    font-size: var(--font-size-small);

    &:hover {
      background: var(--color-yellow-60);
    }

    .unified-search-input-tag-dismiss-icon {
      margin-top: 2px;
    }
  }

  &.provider {
    color: inherit;
    background: var(--success-dimmed-2);

    .unified-search-input-tag-dismiss {
      &:hover {
        background: var(--success);
      }
    }
  }
}

.unified-search-input {
  background: transparent;
  border: 0;
  width: auto;
  line-height: 15px;
  height: 27px;
  padding: 0;
  margin-left: var(--dimension-4);
  flex-grow: 5;

  &::placeholder {
    color: var(--default-form-element-placeholder-color);
  }
}

.unified-search-filter-suggestions {
  position: absolute;
  top: 30px;
  left: var(--spacing-half);
  width: calc(100% - 24px);
  padding: 0;
  background: var(--default-form-element-bg-color);
  height: auto;
}

.unified-search-filter-suggestions-list {
  position: relative;
  padding: 0 8px 16px;
}

.unified-search-icon {
  margin-left: var(--spacing);
  z-index: +1;
}

.unified-search-reset {
  opacity: 0.6;
  margin-right: 3px;
  cursor: pointer;
  position: absolute;
  right: 8px;
}

.unified-search-info-item {
  color: var(--dropdown-chevron-indicator-color);
  opacity: 0.5;
  position: absolute;
  right: 0;
  top: 35px;

  span {
    font-size: var(--font-size-small);
  }

  .arrow-key {
    width: 11px;
    display: inline-flex;
    height: 12px;
    margin-bottom: -4px;

    &::after {
      font-size: 21px;
      position: absolute;
      margin: -8px 0 0 -1px;
    }

    &.enter::after {
      content: '\21B5';
    }
  }
}
</style>
