<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import ResultList from './result/ResultList.vue'
import ResultItem from './result/ResultItem.vue'
import { onBeforeUnmount, ref } from 'vue'
import { HistoryEntry } from '@/lib/unified-search/searchHistory'
import { immediateWatch } from '@/lib/watch'
import type { SearchHistorySearchResult } from '@/lib/unified-search/providers/history'
import { getSearchUtils } from './providers/search-utils'
import {
  providerIcons,
  type UnifiedSearchResultElement
} from '@/lib/unified-search/providers/unified'

const { t } = usei18n('unified-search-app')

const maxRecentlyViewed = 5
const maxRecentlySearched = 5
const recentlyViewed = ref<HistoryEntry[]>([])
const recentlySearches = ref<string[]>([])

const searchUtils = getSearchUtils()

const currentlySelected = ref<number>(-1)
searchUtils.input?.onSetFocus(() => {
  currentlySelected.value = -1
})

const scCallbackIds = ref<string[]>([])
scCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
scCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))

function toggleDown() {
  calcCurrentlySelected(+1)
}

function toggleUp() {
  calcCurrentlySelected(-1)
}

function calcCurrentlySelected(d: number, set: boolean = false) {
  if (set) {
    currentlySelected.value = d
  } else {
    currentlySelected.value += d
  }

  if (
    currentlySelected.value === -1 ||
    currentlySelected.value > recentlyViewed.value.length + recentlySearches.value.length - 1
  ) {
    currentlySelected.value = -1
    searchUtils.input?.setFocus()
    return
  }

  if (currentlySelected.value < 0) {
    currentlySelected.value += recentlyViewed.value.length + recentlySearches.value.length + 1
    return
  }
}

function handleItemClick(item: UnifiedSearchResultElement) {
  searchUtils.history?.add(new HistoryEntry(searchUtils.query.value, item))
  searchUtils.closeSearch()
}

const isFocused = (i: number): boolean => currentlySelected.value === i

const props = defineProps<{
  historyResult?: SearchHistorySearchResult | null | undefined
}>()

immediateWatch(
  () => ({ newHistoryResult: props.historyResult }),
  async ({ newHistoryResult }) => {
    if (newHistoryResult) {
      const res = await newHistoryResult.result
      if (res) {
        recentlyViewed.value = res.entries
        recentlySearches.value = res.queries
        return
      }
    }

    recentlyViewed.value = searchUtils.history?.getEntries(null, 'date', maxRecentlyViewed) || []
    recentlySearches.value = searchUtils.history?.getQueries(maxRecentlySearched) || []
  }
)

onBeforeUnmount(() => {
  searchUtils.shortCuts.remove(scCallbackIds.value)
})
</script>

<template>
  <div v-if="recentlyViewed.length > 0" class="recently-viewed">
    <h2>
      {{ t('recently-viewed', 'Recently viewed') }}
      <button
        @click="
          () => {
            searchUtils.history?.resetEntries()
            recentlyViewed = []
          }
        "
      >
        {{ t('clear-all', 'Clear all') }}
      </button>
    </h2>
    <ResultList>
      <ResultItem
        v-for="(item, idx) in recentlyViewed"
        ref="recently-viewed-item"
        :key="item.element.url"
        :title="item.element.title"
        :context="item.element.context"
        :icon="providerIcons[item.element.provider]"
        :url="item.element.url"
        :html="searchUtils.highlightQuery(item.element.title)"
        :provider="item.element.provider"
        :topic="item.element.topic"
        :breadcrumb="searchUtils.breadcrumb(item.element.provider, item.element.topic)"
        :focus="isFocused(idx)"
        @keypress.enter="
          () => {
            handleItemClick(item.element)
          }
        "
        @click="
          () => {
            handleItemClick(item.element)
          }
        "
      ></ResultItem>
    </ResultList>
  </div>

  <div v-if="recentlySearches.length > 0" class="recent-searches">
    <h2>
      {{ t('recently-searched', 'Recently searched') }}
      <button
        @click="
          () => {
            searchUtils.history?.resetQueries()
            recentlySearches = []
          }
        "
      >
        {{ t('clear-all', 'Clear all') }}
      </button>
    </h2>
    <ResultList>
      <ResultItem
        v-for="(q, idx) in recentlySearches"
        ref="recently-searched-item"
        :key="q"
        :title="q"
        :icon="{
          name: 'history'
        }"
        :html="searchUtils.highlightQuery(q)"
        :focus="isFocused(idx + recentlyViewed.length)"
        @click="
          () => {
            searchUtils.input?.setValue(q)
          }
        "
      ></ResultItem>
    </ResultList>
  </div>
</template>

<style scoped>
h2 {
  margin-bottom: 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

button {
  border: 0;
  background: 0;
  font-weight: normal;
  background: transparent;
  margin-right: 0;
  text-decoration: underline;
  border: 1px solid transparent;

  &:hover {
    background-color: var(--ux-theme-5);
    text-decoration: none;
  }

  &:focus {
    border: 1px solid var(--success);
  }
}

.recently-viewed,
.recent-searches {
  margin: 20px;
}
</style>
