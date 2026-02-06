<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { OneColorIcons } from '@/components/CmkIcon/types'

import type { UnifiedSearchProvider } from '@/unified-search/lib/providers/unified'
import { getSearchUtils } from '@/unified-search/providers/search-utils'
import type { ProviderOption, QueryProvider } from '@/unified-search/providers/search-utils.types'

import { availableProviderOptions } from '../QueryOptions'
import FilterButton from './FilterButton.vue'

const { _t } = usei18n()
const searchUtils = getSearchUtils()

const configuredProviders =
  (searchUtils.search?.get('unified') as UnifiedSearchProvider)?.providers || []

const availableProviders = availableProviderOptions.filter((po) => {
  return (
    (po.value === 'all' && configuredProviders.length > 1) ||
    (po.value !== 'all' && configuredProviders.indexOf(po.value) >= 0)
  )
})

searchUtils.input.onSetProviderValue(onSetProviderValue)

function onSetProviderValue(selected: ProviderOption | undefined): void {
  if (selected) {
    searchUtils.query.provider.value = selected.value
  }

  searchUtils.input.setQuery(searchUtils.query.toQueryLike())
}

function selectProvider(providerOption: ProviderOption) {
  searchUtils.input.setProviderValue(providerOption)
}

const provideri18n: Record<QueryProvider, TranslatedString> = {
  all: _t('All'),
  monitoring: _t('Monitoring'),
  customize: _t('Customize'),
  setup: _t('Setup')
}
</script>

<template>
  <div class="unified-search-search-provider__wrapper">
    <FilterButton
      v-for="po in availableProviders"
      :key="po.value"
      :active="searchUtils.query.provider.value === po.value"
      active-color="success"
      :icon="
        po.value === 'all'
          ? undefined
          : {
              name: po.value as OneColorIcons,
              activeColor: { custom: 'var(--black)' }
            }
      "
      @click="selectProvider(po)"
    >
      {{ provideri18n[po.value] }}
    </FilterButton>
  </div>
</template>

<style scoped>
.unified-search-search-provider__wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
