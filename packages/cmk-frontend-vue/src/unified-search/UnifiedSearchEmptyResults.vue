<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkButton from '@/components/CmkButton.vue'
import { getSearchUtils } from './providers/search-utils'
import type { HistoryEntry } from '@/lib/unified-search/searchHistory'
import { onBeforeUnmount, ref, useTemplateRef } from 'vue'
import UnifiedSearchRecentlyViewed from './UnifiedSearchRecentlyViewed.vue'

const maxRecentlyViewed = 5

const { t } = usei18n('unified-search-app')
const searchUtils = getSearchUtils()
const recentlyViewed = ref<HistoryEntry[]>(
  searchUtils.history?.getEntries(null, 'date', maxRecentlyViewed) || []
)

const resetButton = useTemplateRef('reset-button')
const currentlySelected = ref<number>(-1)
searchUtils.input?.onSetFocus(() => {
  currentlySelected.value = -1
})

const scCallbackIds = ref<string[]>([])
scCallbackIds.value.push(searchUtils.shortCuts.onArrowDown(toggleDown))
scCallbackIds.value.push(searchUtils.shortCuts.onArrowUp(toggleUp))

function toggleDown() {
  console.log('toggleDown')
  calcCurrentlySelected(+1)
}

function toggleUp() {
  console.log('toggleUp')
  calcCurrentlySelected(-1)
}

function calcCurrentlySelected(d: number, set: boolean = false) {
  if (set) {
    currentlySelected.value = d
  } else {
    currentlySelected.value += d
  }

  if (currentlySelected.value === 0) {
    resetButton.value?.$el.focus()
  }

  if (currentlySelected.value === -1 || currentlySelected.value > recentlyViewed.value.length) {
    currentlySelected.value = -1
    searchUtils.input?.setFocus()
    return
  }

  if (currentlySelected.value < 0) {
    currentlySelected.value = recentlyViewed.value.length
    return
  }
}

onBeforeUnmount(() => {
  searchUtils.shortCuts.remove(scCallbackIds.value)
})
</script>

<template>
  <div class="cmk-unified-search-empty-result">
    <div class="shruggy">{{ t('shruggy', '¯\\_(ツ)_/¯') }}</div>
    <div>
      {{ t('no-results-found', 'No results found for your search') }}
    </div>
    <CmkButton ref="reset-button" class="reset-button" @click.stop="searchUtils.resetSearch()">
      <CmkIcon name="reload"></CmkIcon>
      {{ t('reset-search', 'Reset search') }}
    </CmkButton>
  </div>
  <UnifiedSearchRecentlyViewed
    :focus="currentlySelected - 1"
    :history-entries="recentlyViewed"
  ></UnifiedSearchRecentlyViewed>
</template>

<style scoped>
.cmk-unified-search-empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;

  .shruggy {
    font-size: 38px;
    margin: 64px 0;
  }

  .reset-button {
    margin: 32px 0;
    gap: 8px;

    &:focus {
      border: 1px solid var(--success);
    }
  }
}
</style>
