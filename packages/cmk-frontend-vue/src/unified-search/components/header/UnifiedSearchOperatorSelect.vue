<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import CmkIcon from '@/components/CmkIcon.vue'

import type { FilterOption } from '@/unified-search/providers/search-utils.types'

import { getSearchUtils } from '../../providers/search-utils'
import DropDownIndicator from './DropDownIndicator.vue'
import { availableFilterOptions } from './QueryOptions'
import SearchOperatorOptionEntry from './SearchOperatorOptionEntry.vue'

const { _t } = usei18n()
const searchUtils = getSearchUtils()
const operatorDropdownBtn = useTemplateRef('unified-search-operator-btn')
const filterOptions = ref<FilterOption[]>(availableFilterOptions)
const props = defineProps<{
  disabled?: boolean | undefined
}>()

const vClickOutside = useClickOutside()
function handleOperatorSelect(selected: FilterOption): void {
  let newInput = searchUtils.query.input.value
  if (newInput.length === 0) {
    newInput = selected.value
  } else {
    newInput = newInput.concat(selected.value)
  }

  searchUtils.input.setInputValue(newInput)

  hideOperatorOptions()
}

const currentlySelected = ref<number>(-1)
const isFocused = (i: number): boolean =>
  currentlySelected.value === i && searchUtils.input.searchOperatorSelectActive.value === true

const shortcutCallbackIds = ref<string[]>([])
shortcutCallbackIds.value.push(searchUtils.shortCuts.onEscape(hideOperatorOptions))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))

function toggleDown() {
  calcCurrentlySelected(+1)
}

function toggleUp() {
  calcCurrentlySelected(-1)
}

function calcCurrentlySelected(d: number, set: boolean = false) {
  if (searchUtils.input.searchOperatorSelectActive.value === true) {
    if (set) {
      currentlySelected.value = d
    } else {
      currentlySelected.value += d
    }

    if (
      currentlySelected.value === -1 ||
      currentlySelected.value > filterOptions.value.length - 1
    ) {
      currentlySelected.value = -1
      operatorDropdownBtn.value?.focus()
      return
    }

    if (currentlySelected.value < 0) {
      currentlySelected.value += filterOptions.value.length + 1
      return
    }
  }
}

function showOperatorOptions() {
  searchUtils.input.searchOperatorSelectActive.value = true
  searchUtils.input.providerSelectActive.value = false
  searchUtils.input.hideSuggestions()
}

function hideOperatorOptions() {
  if (searchUtils.input.searchOperatorSelectActive.value === true) {
    searchUtils.input.searchOperatorSelectActive.value = false
    searchUtils.input.setFocus()
    currentlySelected.value = -1
  }
}
function toggleOperatorOptions() {
  if (searchUtils.input.searchOperatorSelectActive.value) {
    hideOperatorOptions()
  } else {
    showOperatorOptions()
  }
}
</script>

<template>
  <div class="unified-search-operator-switch" :class="{ disabled: props.disabled }">
    <button
      ref="unified-search-operator-btn"
      class="unified-search-operator-switch-button"
      :class="{ active: searchUtils.input.searchOperatorSelectActive.value }"
      :disabled="props.disabled"
      :title="props.disabled ? _t('Only available for \'Monitoring\' and \'All\'') : ''"
      @click.stop="toggleOperatorOptions"
      @keypres.enter.stop="toggleOperatorOptions"
    >
      <CmkIcon name="info" size="small" class="unified-search-operator-info-icon"></CmkIcon>
      <span class="unified-search-operator-switch-selected">{{ _t('Search operators') }}</span>
      <DropDownIndicator
        class="unified-search-operator-switch-indicator"
        :active="searchUtils.input.searchOperatorSelectActive.value"
      ></DropDownIndicator>
    </button>
    <div
      v-if="searchUtils.input.searchOperatorSelectActive.value"
      v-click-outside="hideOperatorOptions"
      class="unified-search-operator-options"
    >
      <ul class="unified-search-operator-option-list">
        <li class="unified-search-operator-option-list-section-title">
          {{ _t('Type "/" to use search operator') }}
        </li>
        <SearchOperatorOptionEntry
          v-for="(opt, idx) in filterOptions"
          :key="opt.type.concat(opt.value)"
          :class="[opt.type, { separator: idx === 5 }]"
          :focus="isFocused(idx)"
          :idx="idx"
          :option="opt"
          @click.stop="() => handleOperatorSelect(opt)"
          @keypres.enter.stop="() => handleOperatorSelect(opt)"
        ></SearchOperatorOptionEntry>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.unified-search-operator-switch {
  border-radius: var(--border-radius);
  border: 1px solid transparent;
  height: 27px;

  &:hover,
  &.active {
    background: var(--ux-theme-5);
  }

  .unified-search-operator-switch-button {
    height: 100%;
    padding: 0 var(--dimension-3) 0 var(--dimension-4);
    display: flex;
    flex-direction: row;
    align-items: center;
    margin: 0;
    background: transparent;
    font-weight: var(--font-weight-default);
    border: 1px solid transparent;

    &:focus-visible {
      color: var(--success);
      border: 1px solid var(--success);
    }

    .unified-search-operator-switch-selected {
      &::first-letter {
        text-transform: capitalize;
      }
    }

    .unified-search-operator-switch-indicator {
      padding: 0 0 0 var(--dimension-4);
    }

    .unified-search-operator-info-icon {
      background: var(--color-dark-blue-50);
      border-radius: 99px;
      padding: var(--dimension-3);
      margin-right: var(--dimension-4);
    }
  }

  &.disabled {
    background: transparent;

    .unified-search-operator-switch-indicator,
    .unified-search-operator-info-icon,
    .unified-search-operator-info-icon:hover {
      opacity: 0.5 !important;
    }
  }
}

.unified-search-operator-options {
  position: absolute;
  margin-top: var(--dimension-2);
  right: var(--spacing-double);
  padding: 0;
  background: var(--default-form-element-bg-color);
  height: auto;
  border-bottom-left-radius: var(--border-radius-half);
  border-bottom-right-radius: var(--border-radius-half);
}

.unified-search-operator-option-list-section-title {
  opacity: 0.5;
  font-weight: var(--font-weight-bold);
  padding: var(--dimension-2) var(--dimension-3) !important;
}

.unified-search-operator-option-list {
  position: relative;
  border: 1px solid var(--ux-theme-6);
  padding: 0;
  margin: 0;
}

.separator {
  border-bottom: 1px solid var(--ux-theme-6);
}
</style>
