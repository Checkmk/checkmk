<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

import usei18n from '@/lib/i18n'
import {
  type UnifiedSearchResultElement,
  type UnifiedSearchResultResponse
} from '@/lib/unified-search/providers/unified'
import { HistoryEntry } from '@/lib/unified-search/searchHistory'
import { immediateWatch } from '@/lib/watch'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { getSearchUtils } from '../../providers/search-utils'
import ResultItem from '../result/ResultItem.vue'
import ResultList from '../result/ResultList.vue'
import UnifiedSearchEmptyResults from './UnifiedSearchEmptyResults.vue'

const { _t } = usei18n()

const searchUtils = getSearchUtils()
const currentlySelected = ref<number>(-1)
const inited = ref<boolean>(false)
const results = ref<UnifiedSearchResultElement[]>([])
searchUtils.input?.onSetFocus(() => {
  currentlySelected.value = -1
})

const shortcutCallbackIds = ref<string[]>([])
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
shortcutCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))

function toggleDown() {
  calcCurrentlySelected(+1)
}

function toggleUp() {
  calcCurrentlySelected(-1)
}

function calcCurrentlySelected(d: number, set: boolean = false) {
  if (
    searchUtils.input.suggestionsActive.value === false &&
    searchUtils.input.providerSelectActive.value === false &&
    searchUtils.input.searchOperatorSelectActive.value === false &&
    searchResultNotEmpty()
  ) {
    if (set) {
      currentlySelected.value = d
    } else {
      currentlySelected.value += d
    }

    const curTabResLength = results.value.length || 0

    if (currentlySelected.value === -1 || currentlySelected.value > curTabResLength - 1) {
      currentlySelected.value = -1
      searchUtils.input?.setFocus()
      return
    }

    if (currentlySelected.value < -1) {
      currentlySelected.value = curTabResLength - 1
    }
  }
}

function handleItemClick(item: UnifiedSearchResultElement) {
  searchUtils.history?.add(new HistoryEntry(searchUtils.query.toQueryLike(), item))
  searchUtils.resetSearch()
  searchUtils.closeSearch()
}

const isFocused = (i: number): boolean => currentlySelected.value === i

const props = defineProps<{
  result?: UnifiedSearchResultResponse | undefined
}>()

immediateWatch(
  () => ({ newResult: props.result }),
  async ({ newResult }) => {
    if (newResult) {
      results.value = newResult.results
      inited.value = true
    }
  }
)

onBeforeUnmount(() => {
  searchUtils.shortCuts.remove(shortcutCallbackIds.value)
})

function searchResultNotEmpty(): boolean {
  return results.value.length > 0
}
</script>

<template>
  <div v-if="searchResultNotEmpty()" class="cmk-unified-search-result-tabs">
    <div>
      <CmkHeading type="h4" class="result-heading">
        {{ _t('Results') }} ({{ results.length }})
      </CmkHeading>
    </div>
    <CmkScrollContainer max-height="calc(100vh - 210px)">
      <ResultList>
        <ResultItem
          v-for="(item, idx) in results"
          ref="recently-viewed-item"
          :key="item.url ? item.url : item.title"
          :idx="idx"
          :title="item.title"
          :context="item.context"
          :icon="searchUtils.mapIcon(item.topic, item.provider)"
          :inline-buttons="item.inlineButtons"
          :url="item.url"
          :html="searchUtils.highlightQuery(item.title)"
          :breadcrumb="searchUtils.breadcrumb(item.provider, item.topic)"
          :focus="isFocused(idx)"
          @keypress.enter="
            () => {
              handleItemClick(item)
            }
          "
          @click="
            () => {
              handleItemClick(item)
            }
          "
        ></ResultItem>
      </ResultList>
    </CmkScrollContainer>
  </div>
  <UnifiedSearchEmptyResults v-if="inited && !searchResultNotEmpty()"></UnifiedSearchEmptyResults>
</template>

<style scoped>
.result-heading {
  margin-bottom: var(--spacing);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.cmk-unified-search-tab-info {
  position: absolute;
  right: var(--spacing-double);
  margin-top: 3px;
  line-height: 14px;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-default);
  opacity: 0.5;

  .arrow-key {
    width: 11px;
    display: inline-flex;
    height: 12px;
    margin-bottom: -4px;

    &::after {
      font-size: 21px;
      position: absolute;
      margin: -4px 0 0 -5px;
    }

    &.left::after {
      content: '\2190';
    }

    &.right::after {
      content: '\2192';
    }
  }
}

.arrow-key {
  width: 11px;
  display: inline-flex;
  height: 12px;
  margin-bottom: -4px;

  &::after {
    font-size: 21px;
    position: absolute;
    margin: -4px 0 0 -5px;
  }

  &.left::after {
    content: '\2190';
  }

  &.right::after {
    content: '\2192';
  }

  &.up::after {
    content: '\2191';
    font-size: 12px;
    margin: 0;
  }

  &.down::after {
    content: '\2193';
    font-size: 12px;
    margin: 0;
  }

  &.enter::after {
    content: '\21B5';
  }
}

.cmk-unified-search-result-tabs {
  margin: var(--spacing-double);
  height: 100%;
}
</style>
