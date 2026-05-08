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
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import DefaultPopup from '@/main-menu/changes/components/DefaultPopup.vue'
import { getInjectedMainMenu } from '@/main-menu/provider/main-menu'
import {
  type SearchHistoryResult,
  SearchHistorySearchProvider
} from '@/unified-search/lib/providers/history'
import { UnifiedSearchProvider } from '@/unified-search/lib/providers/unified'
import { SearchHistoryService } from '@/unified-search/lib/searchHistory'
import {
  type SearchProviderResult,
  UnifiedSearch,
  UnifiedSearchAborted,
  UnifiedSearchError,
  type UnifiedSearchResult
} from '@/unified-search/lib/unified-search'

import UnifiedSearchInputInjector from './components/UnifiedSearchInputInjector.vue'
import UnifiedSearchHeader from './components/header/UnifiedSearchHeader.vue'
import UnifiedSearchStart from './components/view/UnifiedSearchStart.vue'
import UnifiedSearchTabResults from './components/view/UnifiedSearchTabResults.vue'
import UnifiedSearchWaitForResults from './components/view/UnifiedSearchWaitForResults.vue'
import { getIconForTopic } from './lib/icon-mapping'
import { setRecentSearch } from './lib/search-debug'
import { initSearchUtils, provideSearchUtils } from './providers/search-utils'
import type { UnifiedSearchQueryLike } from './providers/search-utils.types'

const { _t } = usei18n()

const props = defineProps<UnifiedSearchProps>()
const mainMenu = getInjectedMainMenu()

const searchId = `unified-search-${props.edition}-${props.site}-${props.user_id}`

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
      manipulatedMessage.value = uspr.manipulatedMessage
      originQuery.value = uspr.originalQuery
      isManipulated.value = uspr.isManipulated || false
      const usprRes = await uspr.result

      if (usprRes instanceof UnifiedSearchAborted) {
        return
      }

      if (usprRes instanceof UnifiedSearchError) {
        searchError.value = usprRes
        searchResult.value = undefined
      } else {
        if (usprRes) {
          usprRes.results = usprRes.results.map((i: UnifiedSearchResultItem) => {
            i.icon = getIconForTopic(i.topic, i.provider, props.icons_per_item)

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
  async function setHistoryResults(hpr: SearchProviderResult<SearchHistoryResult>) {
    if (hpr) {
      const hprRes = (await hpr.result) as SearchHistoryResult
      historyResult.value = hprRes
    } else {
      historyResult.value = undefined
    }
  }

  if (
    (search.get('search-history') as UnifiedSearchProvider).shouldExecuteSearch(
      searchUtils.query.toQueryLike()
    )
  ) {
    void setHistoryResults(
      result?.get('search-history') as SearchProviderResult<SearchHistoryResult>
    )
  }

  if (
    (search.get('unified') as UnifiedSearchProvider).shouldExecuteSearch(
      searchUtils.query.toQueryLike()
    )
  ) {
    void setSearchResults(result?.get('unified') as SearchProviderResult<UnifiedSearchApiResponse>)
  }
})

const searchResult = ref<UnifiedSearchApiResponse>()
const searchError = ref<UnifiedSearchError>()
const historyResult = ref<SearchHistoryResult>()
const waitForSearchResults = ref<boolean>(false)
const searchUtils = initSearchUtils(searchId)
const manipulatedMessage = ref<TranslatedString>()
const originQuery = ref<UnifiedSearchQueryLike>()
const isManipulated = ref<boolean>(false)

searchUtils.search = search
searchUtils.history = searchHistoryService

provideSearchUtils(searchUtils)

searchUtils.onResetSearch(() => {
  setTimeout(() => {
    searchResult.value = undefined
    historyResult.value = undefined
    searchUtils.input.setProviderValue({ type: 'provider', value: 'all', title: 'all' })
  })
})

searchUtils.onCloseSearch(() => {
  mainMenu.close()
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

function showEmptyStart(): boolean {
  return (
    !waitForSearchResults.value &&
    !showTabResults() &&
    !(search.get('unified') as UnifiedSearchProvider).shouldExecuteSearch(
      searchUtils.query.toQueryLike()
    )
  )
}

onMounted(() => {
  searchUtils.shortCuts.enable()
})
</script>

<template>
  <DefaultPopup class="unified-search-app" role="dialog" :aria-label="_t('Search')">
    <UnifiedSearchHeader> </UnifiedSearchHeader>
    <UnifiedSearchStart v-if="showEmptyStart()" :history-result="historyResult">
    </UnifiedSearchStart>
    <UnifiedSearchWaitForResults v-if="waitForSearchResults"> </UnifiedSearchWaitForResults>
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
  background: var(--ux-theme-1);
  z-index: +1;
  left: 0;
  top: 58px;
  bottom: 0;
  border-right: 4px solid var(--default-nav-popup-border-color);
  border-top-width: 0;
  width: 500px;
  max-width: 500px;
}
</style>
