<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ProviderName } from 'cmk-shared-typing/typescript/unified_search'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import { getSearchUtils } from '../providers/search-utils'
import type { SearchProviderKeys } from '../providers/search-utils.types'
import { availableProviderOptions } from './header/QueryOptions'
import UnifiedSearchProviderSelect from './header/UnifiedSearchProviderSelect.vue'

const { _t } = usei18n()
const searchUtils = getSearchUtils()

const props = defineProps<{
  providers: SearchProviderKeys[]
}>()

function goToSearch(e: Event, provider: ProviderName) {
  const input = e.target

  if (input instanceof HTMLInputElement) {
    searchUtils.input.setInputValue(input.value)
    input.value = ''
  }

  searchUtils.input.setProviderValue(
    availableProviderOptions.filter((f) => f.value === provider)[0]
  )

  searchUtils.openSearch()
}
</script>

<template>
  <Teleport
    v-for="provider in props.providers"
    :key="provider"
    :to="`#main_menu_${provider}>div>div`"
  >
    <div class="unified-search-input-injector__root">
      <UnifiedSearchProviderSelect
        :provider="provider"
        :open-search-on-change="true"
      ></UnifiedSearchProviderSelect>
      <CmkIcon class="unified-search-input-injector__icon" name="search" size="medium"></CmkIcon>
      <input
        :id="`unified-search-input-${provider}`"
        role="search"
        class="unified-search-input-injector__input"
        :aria-label="_t(`Search in ${provider}`)"
        :placeholder="_t(`Search in ${provider}`)"
        @input="goToSearch($event, provider)"
      />
    </div>
  </Teleport>
</template>

<style scoped>
.unified-search-input-injector__root {
  background-color: var(--default-form-element-bg-color);
  box-shadow: none;
  filter: none;
  padding: 0;
  width: 100%;
  border-radius: var(--border-radius);
  border: 1px solid var(--default-form-element-border-color);
  line-height: 15px;
  height: 27px;
  margin: 0 var(--dimension-7);
  position: relative;
  display: flex;
  align-items: center;

  &:focus-within {
    border: 1px solid var(--success);
  }
}

.unified-search-input-injector__input {
  background: transparent;
  border: 0;
  width: auto;
  line-height: 15px;
  height: 27px;
  padding: 0;
  margin-left: var(--dimension-4);
  flex-grow: 5;

  &::placeholder {
    color: var(--default-form-element-placeholder-color);
  }
}

.unified-search-input-injector__icon {
  margin-left: var(--spacing);
  z-index: +1;
}
</style>
