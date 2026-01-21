<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeUnmount, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { HistoryEntry } from '@/unified-search/lib/searchHistory'
import type { UnifiedSearchError } from '@/unified-search/lib/unified-search'
import { getSearchUtils } from '@/unified-search/providers/search-utils'

import UnifiedSearchRecentlyViewed from './UnifiedSearchRecentlyViewed.vue'

const maxRecentlyViewed = 5

const { _t } = usei18n()

defineProps<{
  error?: UnifiedSearchError | undefined
}>()

const searchUtils = getSearchUtils()
const recentlyViewed = ref<HistoryEntry[]>(
  searchUtils.history?.getEntries(null, 'date', maxRecentlyViewed) || []
)

const resetButton = useTemplateRef('reset-button')
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
}

onBeforeUnmount(() => {
  searchUtils.shortCuts.remove(shortcutCallbackIds.value)
})
</script>

<template>
  <div class="unified-search-empty-results">
    <CmkAlertBox v-if="error" class="unified-search-empty-results__error" variant="error">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-html="error.message"></div>
    </CmkAlertBox>
    <template v-else>
      <div class="shruggy">{{ _t('¯\\_(ツ)_/¯') }}</div>
      <CmkParagraph>
        {{ _t('No results found for your search') }}
      </CmkParagraph>
    </template>

    <CmkButton ref="reset-button" class="reset-button" @click.stop="searchUtils.resetSearch()">
      <CmkIcon name="reload"></CmkIcon>
      {{ _t('Reset search') }}
    </CmkButton>
  </div>
  <UnifiedSearchRecentlyViewed
    :focus="currentlySelected - 1"
    :history-entries="recentlyViewed"
  ></UnifiedSearchRecentlyViewed>
</template>

<style scoped>
.unified-search-empty-results {
  display: flex;
  flex-direction: column;
  align-items: center;

  .unified-search-empty-results__error {
    margin: var(--spacing-double);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .shruggy {
    font-size: 38px;
    margin: calc(6 * var(--spacing)) 0;
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .reset-button {
    margin: calc(3 * var(--spacing)) 0;
    gap: var(--spacing);

    &:focus {
      border: 1px solid var(--success);
    }
  }
}
</style>
