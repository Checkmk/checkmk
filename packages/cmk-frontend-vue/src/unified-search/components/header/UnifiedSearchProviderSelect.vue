<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import type { ProviderOption, QueryProvider } from '@/unified-search/providers/search-utils.types'

import { getSearchUtils } from '../../providers/search-utils'
import DropDownIndicator from './DropDownIndicator.vue'
import ProviderOptionEntry from './ProviderOptionEntry.vue'
import { availableProviderOptions } from './QueryOptions'

const { _t } = usei18n()
const searchUtils = getSearchUtils()
const providerDropdownBtn = useTemplateRef('unified-search-provider-btn')
const providerOptions = ref<ProviderOption[]>(availableProviderOptions)

const vClickOutside = useClickOutside()
function handleOptionSelect(selected: ProviderOption): void {
  searchUtils.input.setProviderValue(selected)
}

searchUtils.input.onSetProviderValue(onSetProviderValue)

function onSetProviderValue(
  selected: ProviderOption | undefined,
  noSet?: boolean | undefined
): void {
  if (!noSet && selected) {
    searchUtils.query.provider.value = selected.value
    searchUtils.input.setQuery(searchUtils.query.toQueryLike())
  }

  hideProviderOptions()
}

const currentlySelected = ref<number>(-1)
const isFocused = (i: number): boolean =>
  currentlySelected.value === i && searchUtils.input.providerSelectActive.value === true

const shortcutCallbackIds = ref<string[]>([])
shortcutCallbackIds.value.push(searchUtils.shortCuts.onEscape(hideProviderOptions))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))

function toggleDown() {
  calcCurrentlySelected(+1)
}

function toggleUp() {
  calcCurrentlySelected(-1)
}

function calcCurrentlySelected(d: number, set: boolean = false) {
  if (searchUtils.input.providerSelectActive.value === true) {
    if (set) {
      currentlySelected.value = d
    } else {
      currentlySelected.value += d
    }

    if (
      currentlySelected.value === -1 ||
      currentlySelected.value > providerOptions.value.length - 1
    ) {
      currentlySelected.value = -1
      providerDropdownBtn.value?.focus()
      return
    }

    if (currentlySelected.value < 0) {
      currentlySelected.value += providerOptions.value.length + 1
      return
    }
  }
}

function showProviderOptions() {
  searchUtils.input.providerSelectActive.value = true
  searchUtils.input.searchOperatorSelectActive.value = false
  searchUtils.input.hideSuggestions()
}

function hideProviderOptions() {
  if (searchUtils.input.providerSelectActive.value === true) {
    searchUtils.input.providerSelectActive.value = false
    searchUtils.input.setFocus()
    currentlySelected.value = -1
  }
}
function toggleProviderOptions() {
  if (searchUtils.input.providerSelectActive.value) {
    hideProviderOptions()
  } else {
    showProviderOptions()
  }
}

const provideri18n: Record<QueryProvider, string> = {
  all: _t('All'),
  monitoring: _t('Monitoring'),
  customize: _t('Customize'),
  setup: _t('Setup')
}
</script>

<template>
  <div class="unified-search-provider-switch">
    <button
      ref="unified-search-provider-btn"
      class="unified-search-provider-switch-button"
      @click.stop="toggleProviderOptions"
      @keypres.enter.stop="toggleProviderOptions"
    >
      <span class="unified-search-provider-switch-selected">{{
        provideri18n[searchUtils.query.provider.value]
      }}</span>
      <DropDownIndicator
        class="unified-search-provider-switch-indicator"
        :active="searchUtils.input.providerSelectActive.value"
      ></DropDownIndicator>
    </button>
    <div
      v-if="searchUtils.input.providerSelectActive.value"
      v-click-outside="hideProviderOptions"
      class="unified-search-provider-options"
    >
      <ul class="unified-search-provider-option-list">
        <li class="unified-search-provider-option-list-section-title">
          {{ _t('Search in') }}
        </li>
        <ProviderOptionEntry
          v-for="(opt, idx) in providerOptions"
          :key="opt.type.concat(opt.value)"
          :class="opt.type"
          :focus="isFocused(idx)"
          :idx="idx"
          :option="opt"
          :active="opt.value === searchUtils.query.provider.value"
          @click.stop="() => handleOptionSelect(opt)"
          @keypres.enter.stop="() => handleOptionSelect(opt)"
        ></ProviderOptionEntry>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.unified-search-provider-switch {
  background: var(--ux-theme-7);
  height: 100%;
  border-top-left-radius: var(--border-radius);
  border-bottom-left-radius: var(--border-radius);
  &:hover {
    background: var(--ux-theme-6);
  }

  .unified-search-provider-switch-button {
    height: 100%;
    padding: 0 var(--dimension-3) 0 var(--dimension-4);
    display: flex;
    flex-direction: row;
    align-items: center;
    margin: 0;
    background: transparent;
    border: 0;
    font-weight: var(--font-weight-default);
    border: 1px solid transparent;

    &:focus-visible {
      color: var(--success);
      border: 1px solid var(--success);
    }

    .unified-search-provider-switch-selected {
      &::first-letter {
        text-transform: capitalize;
      }
    }

    .unified-search-provider-switch-indicator {
      padding: 0 0 0 var(--dimension-4);
    }
  }
}

.unified-search-provider-options {
  position: absolute;
  top: 30px;
  left: 0;
  padding: 0;
  background: var(--default-form-element-bg-color);
  height: auto;
  border-bottom-left-radius: var(--border-radius-half);
  border-bottom-right-radius: var(--border-radius-half);
}

.unified-search-provider-option-list-section-title {
  opacity: 0.5;
  font-weight: var(--font-weight-bold);
  padding: var(--dimension-2) var(--dimension-3) !important;
}

.unified-search-provider-option-list {
  position: relative;
  border: 1px solid var(--ux-theme-6);
  padding: 0;
  margin: 0;
}
</style>
