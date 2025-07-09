<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { inject, nextTick, onMounted, ref } from 'vue'
import { UnifiedSearch, type UnifiedSearchResult } from '@/lib/unified-search/unified-search'
import { type Providers } from 'cmk-shared-typing/typescript/unified_search'
import {
  SearchHistorySearchProvider,
  type SearchHistorySearchResult
} from '@/lib/unified-search/providers/history'
import UnifiedSearchHeader from './UnifiedSearchHeader.vue'
import UnifiedSearchStart from './UnifiedSearchStart.vue'
import { apiServiceProvider } from './providers/api'
import { SearchHistoryService } from '@/lib/unified-search/searchHistory'
import { Api } from '@/lib/api-client'
import DefaultPopup from '@/main-menu/DefaultPopup.vue'
import UnifiedSearchTabResults from './UnifiedSearchTabResults.vue'
import { initSearchUtils, provideSearchUtils } from './providers/search-utils'
import {
  UnifiedSearchProvider,
  type UnifiedSearchProviderIdentifier
} from '@/lib/unified-search/providers/unified'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any

const searchId = 'unified-search'

const api = inject(apiServiceProvider, new Api(), true)
const searchHistoryService = new SearchHistoryService(searchId)

const props = defineProps<{
  providers: Providers
}>()

const searchProviderIdentifiers: { id: UnifiedSearchProviderIdentifier; sort: number }[] = []
if (props.providers.setup.active) {
  searchProviderIdentifiers.push({ id: 'setup', sort: props.providers.setup.sort })
}
if (props.providers.monitoring.active) {
  searchProviderIdentifiers.push({ id: 'monitoring', sort: props.providers.monitoring.sort })
}

const searchHistorySearchProvider = new SearchHistorySearchProvider(
  searchHistoryService as SearchHistoryService
)
const search = new UnifiedSearch(searchId, api, [
  new UnifiedSearchProvider(
    searchProviderIdentifiers.sort((a, b) => a.sort - b.sort).map((p) => p.id)
  ),
  searchHistorySearchProvider
])
search.onSearch((result?: UnifiedSearchResult) => {
  searchResult.value = undefined
  void nextTick(() => {
    searchResult.value = result
  })
})
const searchResult = ref<UnifiedSearchResult>()
const searchUtils = initSearchUtils()

searchUtils.search = search
searchUtils.history = searchHistoryService

provideSearchUtils(searchUtils)

searchUtils.onResetSearch(() => {
  searchUtils.query.value = ''
  searchResult.value = undefined
  searchUtils.input.setFocus()
})

searchUtils.onCloseSearch(() => {
  cmk.popup_menu.close_popup()
})

searchUtils.shortCuts.onEscape(() => {
  searchUtils.resetSearch()
  searchUtils.closeSearch()
})

onMounted(() => {
  searchUtils.shortCuts.enable()
})
</script>

<template>
  <DefaultPopup class="unified-search-root" @click.stop>
    <UnifiedSearchHeader> </UnifiedSearchHeader>
    <UnifiedSearchStart
      v-if="searchUtils.query.value.length < 3"
      :history-result="searchResult?.get('search-history') as SearchHistorySearchResult"
    >
    </UnifiedSearchStart>
    <UnifiedSearchTabResults
      v-if="searchResult && searchUtils.query.value.length >= 3"
      :unified-result="searchResult"
    >
    </UnifiedSearchTabResults>
  </DefaultPopup>
</template>

<style scoped>
.unified-search-root {
  position: absolute;
  display: flex;
  flex-direction: column;
  height: calc(100% - 58px);
  background: var(--ux-theme-2);
  z-index: +1;
  left: 0;
  top: 58px;
  border-right: 4px solid var(--success);
  border-top-width: 0;
  width: 750px;
  max-width: 750px;
}

.unified-search-results {
  border-top: 1px solid var(--ux-theme-3);
  border-left: 1px solid var(--ux-theme-3);
}

.unified-search-results > .results:first-of-type {
  border-right: 1px solid var(--ux-theme-3);
}

.results {
  display: flex;
  width: 100%;
  height: calc(100% - 61px);
}

.results:deep(span.hightlight_query) {
  display: inline-block;
  background: var(--color-warning);
  color: --black;
}
</style>
