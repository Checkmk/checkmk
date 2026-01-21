<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  ProviderName,
  UnifiedSearchApiResponse,
  UnifiedSearchProps,
  UnifiedSearchResultItem
} from 'cmk-shared-typing/typescript/unified_search'
import { onMounted, ref } from 'vue'

import { Api } from '@/lib/api-client'

import DefaultPopup from '@/main-menu/changes/components/DefaultPopup.vue'
import {
  SearchHistorySearchProvider,
  type SearchHistorySearchResult
} from '@/unified-search/lib/providers/history'
import { UnifiedSearchProvider } from '@/unified-search/lib/providers/unified'
import { SearchHistoryService } from '@/unified-search/lib/searchHistory'
import {
  type SearchProviderResult,
  UnifiedSearch,
  UnifiedSearchError,
  type UnifiedSearchResult
} from '@/unified-search/lib/unified-search'

import UnifiedSearchInputInjector from './components/UnifiedSearchInputInjector.vue'
import UnifiedSearchHeader from './components/header/UnifiedSearchHeader.vue'
import UnifiedSearchStart from './components/view/UnifiedSearchStart.vue'
import UnifiedSearchTabResults from './components/view/UnifiedSearchTabResults.vue'
import UnifiedSearchWaitForResults from './components/view/UnifiedSearchWaitForResults.vue'
import { getIconByTitle, getIconForTopic } from './lib/icon-mapping'
import { setRecentSearch } from './lib/search-debug'
import { initSearchUtils, provideSearchUtils } from './providers/search-utils'
import type { UnifiedSearchQueryLike } from './providers/search-utils.types'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any

const props = defineProps<UnifiedSearchProps>()

const searchId = `unified-search-${props.user_id}-${props.edition}`

const api = new Api()

const searchHistoryService = new SearchHistoryService(searchId)

const searchProviderIdentifiers: {
  id: ProviderName
  sort: number
}[] = []
if (props.providers.setup.active) {
  searchProviderIdentifiers.push({
    id: 'setup',
    sort: props.providers.setup.sort
  })
}
if (props.providers.customize.active) {
  searchProviderIdentifiers.push({
    id: 'customize',
    sort: props.providers.customize.sort
  })
}
if (props.providers.monitoring.active) {
  searchProviderIdentifiers.push({
    id: 'monitoring',
    sort: props.providers.monitoring.sort
  })
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
  async function setSearchResults(uspr: SearchProviderResult<UnifiedSearchApiResponse>) {
    if (uspr) {
      waitForSearchResults.value = true
      const usprRes = await uspr.result
      if (usprRes instanceof UnifiedSearchError) {
        searchError.value = usprRes
        searchResult.value = undefined
      } else {
        if (usprRes) {
          usprRes.results = usprRes.results.map((i: UnifiedSearchResultItem) => {
            i.icon = getIconForTopic(i.topic, i.provider, props.icons_per_item)
            if (i.inline_buttons) {
              i.inline_buttons = i.inline_buttons.map((ib) => {
                ib.icon = getIconByTitle(ib.title)
                return ib
              })
            }
            return i
          })

          searchError.value = undefined
          searchResult.value = usprRes as UnifiedSearchApiResponse
          setRecentSearch(searchResult.value)
        } else {
          searchResult.value = undefined
        }
      }
      waitForSearchResults.value = false
    } else {
      searchResult.value = undefined
    }
  }
  async function setHistoryResults(hpr: SearchProviderResult<SearchHistorySearchResult>) {
    if (hpr) {
      const hprRes = (await hpr.result) as SearchHistorySearchResult
      historyResult.value = hprRes
    } else {
      historyResult.value = undefined
    }
  }

  void setHistoryResults(
    result?.get('search-history') as SearchProviderResult<SearchHistorySearchResult>
  )
  void setSearchResults(result?.get('unified') as SearchProviderResult<UnifiedSearchApiResponse>)
})

const searchResult = ref<UnifiedSearchApiResponse>()
const searchError = ref<UnifiedSearchError>()
const historyResult = ref<SearchHistorySearchResult>()
const waitForSearchResults = ref<boolean>(true)
const searchUtils = initSearchUtils(searchId)

searchUtils.search = search
searchUtils.history = searchHistoryService

provideSearchUtils(searchUtils)

searchUtils.onResetSearch(() => {
  setTimeout(() => {
    searchResult.value = undefined
  })
})

searchUtils.onCloseSearch(() => {
  cmk.popup_menu.close_popup()
})

searchUtils.input.onSetQuery((query?: UnifiedSearchQueryLike) => {
  if (query && query.input !== '/') {
    search.initSearch(query)
  }
})

searchUtils.shortCuts.onEscape(() => {
  if (
    searchUtils.input.suggestionsActive.value === false &&
    searchUtils.input.providerSelectActive.value === false
  ) {
    searchUtils.resetSearch()
    searchUtils.closeSearch()
  }
})

function showTabResults(): boolean {
  return (
    typeof searchError.value !== 'undefined' ||
    (typeof searchResult.value !== 'undefined' &&
      (search.get('unified') as UnifiedSearchProvider).shouldExecuteSearch(
        searchUtils.query.toQueryLike()
      ))
  )
}

onMounted(() => {
  searchUtils.shortCuts.enable()
})
</script>

<template>
  <DefaultPopup class="unified-search-app">
    <UnifiedSearchHeader> </UnifiedSearchHeader>
    <UnifiedSearchStart v-if="!showTabResults()" :history-result="historyResult">
    </UnifiedSearchStart>
    <UnifiedSearchWaitForResults v-if="waitForSearchResults && showTabResults()">
    </UnifiedSearchWaitForResults>
    <UnifiedSearchTabResults
      v-if="!waitForSearchResults && showTabResults()"
      :result="searchResult"
      :error="searchError"
    >
    </UnifiedSearchTabResults>
  </DefaultPopup>
  <UnifiedSearchInputInjector :providers="searchProviderIdentifiers.map((p) => p.id)" />
</template>

<style scoped>
.unified-search-app {
  position: absolute;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 58px);
  background: var(--ux-theme-1);
  z-index: +1;
  left: 0;
  top: 58px;
  border-right: 4px solid var(--default-nav-popup-border-color);
  border-top-width: 0;
  width: 750px;
  max-width: 750px;
}
</style>
