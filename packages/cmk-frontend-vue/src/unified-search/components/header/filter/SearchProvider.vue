<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkBadge, { type Colors, type Types } from '@/components/CmkBadge.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { CmkMultitoneIconColor, CustomIconColor } from '@/components/CmkIcon/types'

import type { UnifiedSearchProvider } from '@/unified-search/lib/providers/unified'
import { getSearchUtils } from '@/unified-search/providers/search-utils'
import type { ProviderOption, QueryProvider } from '@/unified-search/providers/search-utils.types'

import { availableProviderOptions } from '../QueryOptions'

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

function getProviderBadgeColor(provider: QueryProvider): Colors {
  return searchUtils.query.provider.value === provider ? 'success' : 'default'
}

function getProviderBadgeType(provider: QueryProvider): Types {
  return searchUtils.query.provider.value === provider ? 'fill' : 'outline'
}

function getProviderIconColor(provider: QueryProvider): CmkMultitoneIconColor | CustomIconColor {
  return searchUtils.query.provider.value === provider ? { custom: 'var(--black)' } : 'font'
}
</script>

<template>
  <div class="unified-search-search-provider__wrapper">
    <button
      v-for="po in availableProviders"
      :key="po.value"
      class="unified-search-search-provider__button"
      @click="selectProvider(po)"
    >
      <CmkBadge
        :color="getProviderBadgeColor(po.value)"
        :type="getProviderBadgeType(po.value)"
        size="small"
        class="unified-search-search-provider__chip"
      >
        <CmkMultitoneIcon
          v-if="po.value !== 'all'"
          :name="po.value"
          :primary-color="getProviderIconColor(po.value)"
          size="small"
          class="unified-search-search-provider__icon"
        />
        {{ provideri18n[po.value] }}
      </CmkBadge>
    </button>
  </div>
</template>

<style scoped>
.unified-search-search-provider__wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);

  .unified-search-search-provider__button {
    padding: 0;
    margin: 0;
    border: 0;
    border-radius: 99999px;
    background: transparent;

    &:hover {
      background-color: var(--ux-theme-4);
    }

    .unified-search-search-provider__chip {
      border-width: 1px;
      padding: var(--dimension-3) var(--dimension-4);
      margin: 0;
      font-size: var(--font-size-default);

      /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
      &.cmk-badge--default {
        border-color: var(--ux-theme-6);
      }

      .unified-search-search-provider__icon {
        margin-right: var(--dimension-3);
      }
    }
  }
}
</style>
