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
import { immediateWatch } from '@/lib/watch'
import type { SearchHistorySearchResult } from '@/lib/unified-search/providers/history'
import { getSearchUtils, type UnifiedSearchQueryLike } from './providers/search-utils'
import UnifiedSearchRecentlyViewed from './UnifiedSearchRecentlyViewed.vue'
import type { HistoryEntry } from '@/lib/unified-search/searchHistory'

const { t } = usei18n('unified-search-app')

const maxRecentlyViewed = 5
const maxRecentlySearched = 5
const recentlyViewed = ref<HistoryEntry[]>([])
const recentlySearches = ref<UnifiedSearchQueryLike[]>([])

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
  if (searchUtils.input.suggestionsActive.value === false) {
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
        recentlyViewed.value = res.entries.slice(0, maxRecentlyViewed)
        recentlySearches.value = res.queries.slice(0, maxRecentlySearched)
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
  <UnifiedSearchRecentlyViewed
    :focus="currentlySelected"
    :history-entries="recentlyViewed"
  ></UnifiedSearchRecentlyViewed>

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
        :key="q.input"
        :idx="idx"
        :title="q.input"
        :breadcrumb="q.filters.map((f) => f.value)"
        :icon="{
          name: 'history'
        }"
        :html="searchUtils.highlightQuery(q.input)"
        :focus="isFocused(idx + recentlyViewed.length)"
        @click.stop="
          () => {
            searchUtils.input.setInputValue(q.input)
            searchUtils.input.setFilterValue(q.filters)
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
