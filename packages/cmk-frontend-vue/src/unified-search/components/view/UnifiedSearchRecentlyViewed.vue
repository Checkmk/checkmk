<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'
import { type UnifiedSearchResultElement } from '@/lib/unified-search/providers/unified'
import { HistoryEntry } from '@/lib/unified-search/searchHistory'
import { immediateWatch } from '@/lib/watch'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import { getSearchUtils } from '../../providers/search-utils'
import ResultItem from '../result/ResultItem.vue'
import ResultList from '../result/ResultList.vue'

const { _t } = usei18n()

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
    <CmkHeading type="h4" class="result-heading">
      {{ _t('Recently viewed') }}
      <button
        @click.stop="
          () => {
            searchUtils.history?.resetEntries()
            recentlyViewed = []
          }
        "
      >
        {{ _t('Clear all') }}
      </button>
    </CmkHeading>
    <ResultList>
      <ResultItem
        v-for="(item, idx) in recentlyViewed"
        ref="recently-viewed-item"
        :key="item.element.url"
        :idx="idx"
        :title="item.element.title"
        :context="item.element.context"
        :icon="searchUtils.mapIcon(item.element.topic, item.element.provider)"
        :inline-buttons="item.element.inlineButtons"
        :url="item.element.url"
        :html="searchUtils.highlightQuery(item.element.title)"
        :breadcrumb="searchUtils.breadcrumb(item.element.provider, item.element.topic)"
        :focus="isFocused(idx)"
        @keydown.enter="
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
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.result-heading {
  margin-bottom: var(--spacing);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

button {
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

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.recently-viewed {
  margin: var(--spacing-double);
}
</style>
