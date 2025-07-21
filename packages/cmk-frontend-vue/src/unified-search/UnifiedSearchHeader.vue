<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip from '@/components/CmkChip.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'
import { nextTick, ref, useTemplateRef } from 'vue'
import { getSearchUtils } from './providers/search-utils'
import type { Suggestions } from '@/components/CmkSuggestions.vue'
import CmkSuggestions from '@/components/CmkSuggestions.vue'
import CmkAlertBox from '@/components/CmkAlertBox.vue'

interface CmkWindow extends Window {
  main: Window
}

const { t } = usei18n('unified-search-app')
const searchUtils = getSearchUtils()
const searchInput = useTemplateRef('unified-search-input')
const ctrlEnterHelpShown = ref<boolean>(false)
const filterSuggestionsRef = useTemplateRef('unified-search-filter-suggestions')

const filterSuggestionsShown = ref<boolean>(false)
const filterOptions = ref<Suggestions>({
  type: 'fixed',
  suggestions: [
    { name: 'h:', title: 'h: Host' },
    { name: 's:', title: 's: Service' },
    { name: 'hg:', title: 'hg: Host group' },
    { name: 'sg:', title: 'sg: Service group' },
    { name: 'ad:', title: 'ad: Address' },
    { name: 'al:', title: 'al: Alias' },
    { name: 'tg:', title: 'tg: Host tag' },
    {
      name: 'hl:',
      title: 'hl: Host label (e.g. hl: cmk/os_family:linux)'
    },
    {
      name: 'sl:',
      title: 'sl: Service label (e.g. sl: cmk/os_family:linux)'
    },
    {
      name: 'st:',
      title: 'st: Service state (e.g. st: crit [ok|warn|crit|unkn|pend])'
    }
  ]
})
const selectedFilter = ref<string | null>(null)
const vClickOutside = useClickOutside()
function handleFilterSelect(selected: string | null): void {
  hideFilterSuggestions()
  if (selected) {
    searchUtils.query.value = selected
    searchUtils.search?.initSearch(selected)
    searchUtils.input.setFocus()
  }
  selectedFilter.value = null
  searchUtils.shortCuts.enable()
}

function showFilterSuggestions(): void {
  filterSuggestionsShown.value = true

  void nextTick(() => {
    filterSuggestionsRef.value?.focus()
  })
}

function hideFilterSuggestions() {
  filterSuggestionsShown.value = false
  searchUtils.input.setValue('')
  searchUtils.input.setFocus()
}

searchUtils.input?.onSetFocus(setFocus)
function setFocus() {
  if (searchInput.value) {
    searchInput.value.focus()
    searchInput.value.selectionStart = searchInput.value.selectionEnd =
      searchUtils.query.value.length
  }
}

searchUtils.input?.onSetBlur(setBlur)
function setBlur() {
  searchInput.value?.blur()
}

searchUtils.input?.onSetValue(setValue)
function setValue(query?: string) {
  if (typeof query === 'string') {
    searchUtils.query.value = query
    searchUtils.search?.initSearch(query)
  }

  toggleCtrlEnterHelp()
}

function toggleCtrlEnterHelp() {
  if (searchUtils.query.value.length > 0) {
    ctrlEnterHelpShown.value = true
  } else {
    ctrlEnterHelpShown.value = false
  }
}

function onInput(e: Event) {
  if (searchUtils.query.value.indexOf('/') === 0) {
    searchUtils.shortCuts.disable()
    showFilterSuggestions()
    return
  }

  searchUtils.search?.onInput(e)
  searchUtils.query.value = (e.target as HTMLInputElement).value

  toggleCtrlEnterHelp()
}

searchUtils.shortCuts.onCtrlEnter(onCtrlEnter)
function onCtrlEnter() {
  if (searchUtils.query.value.length > 0) {
    ;(top!.frames as CmkWindow).main.location.href = 'search_open.py?q='.concat(
      searchUtils.query.value
    )
    searchUtils.closeSearch()
  }
}
</script>

<template>
  <div class="unified-search-header">
    <div class="unified-search-input-panel">
      <div class="unified-search-input-wrapper">
        <CmkIcon class="unified-search-icon" name="search" size="medium"></CmkIcon>
        <input
          id="unified-search-input"
          ref="unified-search-input"
          v-model="searchUtils.query.value"
          class="unified-search-input"
          :placeholder="
            t('search-accross', 'Search across Checkmk – type \'/\' for filter options')
          "
          @focus="setFocus"
          @input="onInput"
        />
        <div
          v-if="!!filterSuggestionsShown"
          v-click-outside="hideFilterSuggestions"
          class="unified-search-filter-suggestions"
        >
          <CmkSuggestions
            ref="unified-search-filter-suggestions"
            role="option"
            :suggestions="filterOptions"
            :selected-option="selectedFilter"
            class="unified-search-filter-suggestions-list"
            :focus="filterSuggestionsShown"
            @request-close-suggestions="hideFilterSuggestions"
            @update:selected-option="handleFilterSelect"
            @click.stop
          />
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
        <CmkIcon
          v-if="searchUtils.query.value.length > 0"
          class="unified-search-reset"
          name="close"
          size="small"
          @click.stop="searchUtils.resetSearch"
        ></CmkIcon>
      </div>

      <div class="unified-search-info-item">
        <span>{{ t('press', 'Press') }}</span>
        <CmkChip size="small" :content="t('ctrl', 'Ctrl')"></CmkChip>+<CmkChip
          class="arrow-key enter"
          size="small"
          content=""
        ></CmkChip
        ><br />
        <span>{{ t('to-view-matching-service', 'to view matching service') }}</span>
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

.unified-search-input {
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

  &::placeholder {
    color: var(--default-form-element-placeholder-color);
  }
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

.unified-search-filter-suggestions-info {
  border: 1px solid var(--ux-theme-6);
  border-top: 0;
  margin: 0;
  font-style: italic;
  color: var(--help-text-font-color);
}

.unified-search-input:focus,
.unified-search-input:active {
  border: 1px solid var(--success);
}

.unified-search-icon {
  position: absolute;
  margin-left: 10px;
  z-index: +1;
}

.unified-search-reset {
  margin-left: -25px;
  opacity: 0.6;
  margin-right: 3px;
  cursor: pointer;
}
</style>
