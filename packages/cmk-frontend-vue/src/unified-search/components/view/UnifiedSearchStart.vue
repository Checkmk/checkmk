<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import ResultItem from '@/unified-search/components/result/ResultItem.vue'
import ResultList from '@/unified-search/components/result/ResultList.vue'
import type { SearchHistoryResult } from '@/unified-search/lib/providers/history'
import type { HistoryEntry } from '@/unified-search/lib/searchHistory'
import { getSearchUtils } from '@/unified-search/providers/search-utils'
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

import UnifiedSearchEmptyStart from './UnifiedSearchEmptyStart.vue'
import UnifiedSearchRecentlyViewed from './UnifiedSearchRecentlyViewed.vue'

const { _t } = usei18n()

const maxRecentlyViewed = 5
const maxRecentlySearched = 5
const recentlyViewed = ref<HistoryEntry[]>([])
const recentlySearches = ref<UnifiedSearchQueryLike[]>([])

const searchUtils = getSearchUtils()

const currentlySelected = ref<number>(-1)
searchUtils.input?.onSetFocus(() => {
  currentlySelected.value = -1
})
searchUtils.onResetSearch(() => {
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
    searchUtils.input.searchOperatorSelectActive.value === false
  ) {
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
  historyResult?: SearchHistoryResult | null | undefined
}>()

function handleHistoryResult(searchHistory?: SearchHistoryResult | null) {
  if (searchHistory) {
    recentlyViewed.value = searchHistory.entries.slice(0, maxRecentlyViewed)
    recentlySearches.value = searchHistory.queries.slice(0, maxRecentlySearched)
    return
  }

  recentlyViewed.value = searchUtils.history?.getEntries(null, 'date', maxRecentlyViewed) || []
  recentlySearches.value = searchUtils.history?.getQueries(maxRecentlySearched) || []
}

immediateWatch(
  () => ({ newHistoryResult: props.historyResult }),
  async ({ newHistoryResult }) => {
    handleHistoryResult(newHistoryResult)
  }
)

onBeforeUnmount(() => {
  searchUtils.shortCuts.remove(shortcutCallbackIds.value)
})

onMounted(() => {
  handleHistoryResult()
})
</script>

<template>
  <UnifiedSearchEmptyStart v-if="recentlySearches.length === 0 && recentlyViewed.length === 0">
  </UnifiedSearchEmptyStart>

  <UnifiedSearchRecentlyViewed
    :focus="currentlySelected"
    :history-entries="recentlyViewed"
  ></UnifiedSearchRecentlyViewed>

  <div v-if="recentlySearches.length > 0" class="recent-searches">
    <CmkHeading type="h4" class="result-heading">
      {{ _t('Recently searched') }}
      <button
        @click.stop="
          () => {
            searchUtils.history?.resetQueries()
            recentlySearches = []
          }
        "
      >
        {{ _t('Clear all') }}
      </button>
    </CmkHeading>
    <ResultList>
      <ResultItem
        v-for="(q, idx) in recentlySearches"
        ref="recently-searched-item"
        :key="q.input"
        :idx="idx"
        :title="q.input"
        :breadcrumb="[q.provider]"
        :html="searchUtils.highlightQuery(q.input)"
        :focus="isFocused(idx + recentlyViewed.length)"
        :zebra="true"
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
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.result-heading {
  margin-bottom: var(--spacing);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

button {
  font-weight: var(--font-weight-default);
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

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.recent-searches {
  margin: var(--spacing-double);
}
</style>
