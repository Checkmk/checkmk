<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import usei18n from '@/lib/i18n'
import { getSearchUtils } from './providers/search-utils'
import type { Suggestions } from '@/components/CmkSuggestions.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'

const { t } = usei18n('unified-search-app')

const searchUtils = getSearchUtils()

const sortSuggestions: Suggestions = {
  type: 'fixed',
  suggestions: [
    {
      name: 'none',
      title: 'keep legacy sorting (1. Setup, 2. Monitoring)'
    },
    {
      name: 'alphabetic',
      title: 'alphabetical'
    },
    {
      name: 'weighted_index',
      title: 'Weighted Index (Tanja Keyword Match Quality like)'
    }
  ]
}
</script>

<template>
  <div class="unified-search-footer">
    <div class="sorting">
      <label>{{ t('result-sorting', 'Result sorting') }}</label>
      <CmkDropdown
        :selected-option="searchUtils.query.sort.value"
        :options="sortSuggestions"
        label="Sorting algorythm"
        @update:selected-option="
          (sort) => {
            searchUtils.query.sort.value = sort || 'none'
            searchUtils.input.setQuery(searchUtils.query.toQueryLike())
          }
        "
        @click.stop
      >
      </CmkDropdown>
    </div>
    <div>
      {{
        t(
          'not-found-ask-ai',
          "You looked through the results and still haven't found what you are looking for?"
        )
      }}
    </div>
    <div>
      <CmkIcon variant="inline" name="sparkle" :title="t('ask-ai', 'Ask Checkmk AI')" />
      <a href="https://chat.checkmk.com/" target="_blank">{{ t('ask-ai', 'Go Ask AI') }}</a>
    </div>
  </div>
</template>

<style scoped>
.sorting {
  display: flex;
  flex-direction: row;
  bottom: -24px;
  align-items: center;

  label {
    margin-right: 8px;
  }
}

.unified-search-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  bottom: calc(3 * var(--spacing));
  position: fixed;
  width: 750px;
}
</style>
