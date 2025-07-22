<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip from '@/components/CmkChip.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import usei18n from '@/lib/i18n'
import { useTemplateRef } from 'vue'
import { getSearchUtils, type FilterOption } from './providers/search-utils'

import CmkButton from '@/components/CmkButton.vue'
import UnifiedSearchFilters from './UnifiedSearchFilters.vue'

interface CmkWindow extends Window {
  main: Window
}

const { t } = usei18n('unified-search-app')

const searchUtils = getSearchUtils()
const searchInput = useTemplateRef('unified-search-input')
searchUtils.onResetSearch(() => {
  searchUtils.query.filters.value = []
  searchUtils.query.input.value = ''
  setFocus()
})

searchUtils.input?.onSetFocus(setFocus)
function setFocus() {
  if (searchInput.value) {
    searchInput.value.focus()
    searchInput.value.selectionStart = searchInput.value.selectionEnd =
      searchUtils.query.input.value.length
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

searchUtils.shortCuts.onCtrlEnter(onCtrlEnter)
function onCtrlEnter() {
  if (isMonitoringSearch()) {
    if (searchUtils.query.input.value.length > 0) {
      ;(top!.frames as CmkWindow).main.location.href = 'search_open.py?q='.concat(
        searchUtils.query.input.value
      )
      searchUtils.closeSearch()
    }
  }
}

function isMonitoringSearch(): boolean {
  return searchUtils.query.filters.value.findIndex((f) => f.value === 'setup') === -1
}

function handleDelTagItem(tag: FilterOption) {
  const filters = searchUtils.query.filters.value.slice(0)
  filters.splice(searchUtils.query.filters.value.findIndex((f) => f.value === tag.value))
  searchUtils.input.setFilterValue(filters)
  searchUtils.input.setFocus()
}
</script>

<template>
  <div class="unified-search-header">
    <div class="unified-search-input-panel">
      <div class="unified-search-input-wrapper" @click="searchUtils.input.setFocus">
        <CmkIcon class="unified-search-icon" name="search" size="medium"></CmkIcon>
        <div class="unified-search-input-tag-root">
          <div
            v-for="filterOption in searchUtils.query.filters.value"
            :key="['tag-', filterOption.type, filterOption.value].join('-')"
            :value="filterOption.value"
            class="unified-search-input-tag"
            :class="[{ provider: filterOption.type === 'provider' }]"
          >
            <span>{{ filterOption.value }}</span>
            <CmkButton
              class="unified-search-input-tag-dismiss"
              @click.stop="
                () => {
                  handleDelTagItem(filterOption)
                }
              "
            >
              <CmkIcon
                name="close"
                size="xsmall"
                class="unified-search-input-tag-dismiss-icon"
              ></CmkIcon
            ></CmkButton>
          </div>

          <input
            id="unified-search-input"
            ref="unified-search-input"
            v-model="searchUtils.query.input.value"
            class="unified-search-input"
            :placeholder="
              t('search-accross', 'Search across Checkmk – type \'/\' for filter options')
            "
            @input="onInput"
            @keydown.delete="checkEmptyBackspace"
          />
          <UnifiedSearchFilters></UnifiedSearchFilters>
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
      </div>

      <div v-if="isMonitoringSearch()" class="unified-search-info-item">
        <span>{{ t('press', 'Press') }}</span>
        <CmkChip size="small" :content="t('ctrl', 'Ctrl')"></CmkChip>+<CmkChip
          class="arrow-key enter"
          size="small"
          content=""
        ></CmkChip
        ><br />
        <span>{{ t('to-view-matching-service', 'to view matching services') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.unified-search-header {
  height: 60px;
  min-height: 60px !important;
  z-index: +1;
  width: calc(100% - 40px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--ux-theme-3);
}

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

.unified-search-info-item {
  color: var(--help-text-font-color);
  opacity: 0.5;

  span {
    font-size: 10px;
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

.unified-search-input-wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 70%;
  max-width: 500px;
  position: relative;
}

.unified-search-input-tag-root {
  background-color: var(--default-form-element-bg-color);
  box-shadow: none;
  filter: none;
  padding: 0 35px 0 35px;
  width: 100%;
  border-radius: 4px;
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
  border-radius: 4px;
  height: 20px;
  padding: 0px 4px;
  margin-right: 4px;

  .unified-search-input-tag-dismiss {
    background: transparent;
    border: 0;
    margin: 0 0 0 4px;
    height: 16px;
    max-width: 16px;
    overflow: hidden;
    border-radius: 4px;
    padding: 0;
    width: 16px;
    font-size: 10px;

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
  margin-left: 8px;
  flex-grow: 5;
}

.unified-search-filter-suggestions {
  position: absolute;
  top: 30px;
  left: 4px;
  width: calc(100% - 24px);
  padding: 0;
  background: var(--default-form-element-bg-color);
  height: auto;
}

.unified-search-filter-suggestions-list {
  position: relative;
  padding: 0 8px 16px 8px;
}

.unified-search-input {
  background: transparent;
  border: 0;
  width: auto;
  line-height: 15px;
  height: 27px;
  padding: 0;
  margin-left: 8px;
  flex-grow: 5;

  &::placeholder {
    color: var(--default-form-element-placeholder-color);
  }
}

.unified-search-icon {
  position: absolute;
  margin-left: 10px;
  z-index: +1;
}

.unified-search-reset {
  opacity: 0.6;
  margin-right: 3px;
  cursor: pointer;
  position: absolute;
  right: 8px;
}
</style>
