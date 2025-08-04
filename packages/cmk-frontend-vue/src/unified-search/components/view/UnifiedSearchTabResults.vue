<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import { onBeforeUnmount, ref } from 'vue'
import type { SearchProviderResult, UnifiedSearchResult } from '@/lib/unified-search/unified-search'
import ResultList from '../result/ResultList.vue'
import ResultItem from '../result/ResultItem.vue'
import { immediateWatch } from '@/lib/watch'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import { getSearchUtils } from '../../providers/search-utils'
import {
  providerIcons,
  type UnifiedSearchResultElement,
  type UnifiedSearchResultResponse
} from '@/lib/unified-search/providers/unified'
import CmkChip from '@/components/CmkChip.vue'
import { HistoryEntry } from '@/lib/unified-search/searchHistory'
import UnifiedSearchEmptyResults from './UnifiedSearchEmptyResults.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { t } = usei18n('unified-search-app')

const searchUtils = getSearchUtils()
const currentlySelected = ref<number>(-1)
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
  unifiedResult?: UnifiedSearchResult | undefined
}>()

immediateWatch(
  () => ({ newResult: props.unifiedResult }),
  async ({ newResult }) => {
    if (newResult) {
      const uspr = newResult.get('unified') as SearchProviderResult<UnifiedSearchResultResponse>
      const res = (await uspr.result) as UnifiedSearchResultResponse
      if (res) {
        results.value = res.results
      }
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
      <CmkHeading type="h2">
        {{ t('results', 'Results') }} ({{ results.length }})

        <div class="cmk-unified-search-tab-info">
          <CmkChip class="arrow-key up" size="small" content=""></CmkChip>|<CmkChip
            class="arrow-key down"
            size="small"
            content=""
          ></CmkChip>
          <span>&</span>
          <CmkChip class="arrow-key left" size="small" content=""></CmkChip>|<CmkChip
            class="arrow-key right"
            size="small"
            content=""
          ></CmkChip>
          <span>{{ t('to-nav-results', 'to navigate between results') }}</span>
        </div>
      </CmkHeading>
    </div>
    <CmkScrollContainer max-height="calc(100vh - 260px)">
      <ResultList>
        <ResultItem
          v-for="(item, idx) in results"
          ref="recently-viewed-item"
          :key="item.url ? item.url : item.title"
          :idx="idx"
          :title="item.title"
          :context="item.context"
          :icon="
            ['hosts', 'host name', 'hostalias'].indexOf(item.topic.toLowerCase()) >= 0
              ? { name: 'topic-host', title: item.topic, size: 'xlarge' }
              : providerIcons[item.provider]
          "
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
  <UnifiedSearchEmptyResults v-if="!searchResultNotEmpty()"></UnifiedSearchEmptyResults>
</template>

<style scoped>
h2 {
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
