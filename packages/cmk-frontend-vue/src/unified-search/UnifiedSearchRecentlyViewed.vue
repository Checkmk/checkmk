<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import ResultList from './result/ResultList.vue'
import ResultItem from './result/ResultItem.vue'
import { ref } from 'vue'
import { HistoryEntry } from '@/lib/unified-search/searchHistory'
import { immediateWatch } from '@/lib/watch'
import { getSearchUtils } from './providers/search-utils'
import {
  providerIcons,
  type UnifiedSearchResultElement
} from '@/lib/unified-search/providers/unified'

const { t } = usei18n('unified-search-app')

const recentlyViewed = ref<HistoryEntry[]>([])

const searchUtils = getSearchUtils()

function handleItemClick(item: UnifiedSearchResultElement) {
  searchUtils.history?.add(new HistoryEntry(searchUtils.query.toQueryLike(), item))
  searchUtils.closeSearch()
}

const props = defineProps<{
  historyEntries?: HistoryEntry[] | null | undefined
  focus: number
}>()

function isFocused(idx: number): boolean {
  return idx === props.focus
}

immediateWatch(
  () => ({ newHistoryEntries: props.historyEntries }),
  async ({ newHistoryEntries }) => {
    if (newHistoryEntries) {
      recentlyViewed.value = newHistoryEntries
    }
  }
)
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
        :idx="idx"
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
