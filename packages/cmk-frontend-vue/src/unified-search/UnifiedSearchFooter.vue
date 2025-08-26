<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import ToggleButtonGroup, { type ToggleButtonOption } from '@/components/ToggleButtonGroup.vue'

import { getSearchUtils } from './providers/search-utils'

const { _t } = usei18n()

const searchUtils = getSearchUtils()

const sortOptions: ToggleButtonOption[] = [
  {
    value: 'none',
    label: 'legacy sorting'
  },
  {
    value: 'alphabetic',
    label: 'alphabetical'
  },
  {
    value: 'weighted_index',
    label: 'Weighted Index'
  }
]
</script>

<template>
  <div class="unified-search-footer">
    <div class="sorting">
      <label>{{ _t('Result sorting') }}</label>
      <ToggleButtonGroup
        v-model="searchUtils.query.sort.value"
        :options="sortOptions"
        @update:model-value="
          (model: string) => {
            searchUtils.query.sort.value = model || 'none'
            searchUtils.input.setQuery(searchUtils.query.toQueryLike())
          }
        "
        @click.stop
      />
    </div>
  </div>
</template>

<style scoped>
.sorting {
  display: flex;
  flex-direction: row;
  align-items: center;

  label {
    margin-right: 8px;
  }
}

.unified-search-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  bottom: var(--spacing);
  position: fixed;
  width: 750px;
}
</style>
