<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'
import CmkLabel from '@/components/CmkLabel.vue'

import type { FilterDefinition } from '@/dashboard/components/filter/types.ts'

interface Props {
  title: string
  filters: string[]
  filterDefinitions: Record<string, FilterDefinition>
}

const { _t } = usei18n()
const props = defineProps<Props>()

const emit = defineEmits<{
  'remove-filter': [filterId: string]
}>()
</script>

<template>
  <div class="db-filter-selection-collection__container">
    <CmkLabel variant="title">{{ title }}</CmkLabel>
    <div
      v-for="(filterId, index) in filters"
      :key="index"
      class="db-filter-selection-collection__item"
    >
      <span class="db-filter-selection-collection__item-title">
        {{ props.filterDefinitions[filterId]!.title }}
      </span>
      <button
        class="db-filter-selection-collection__item-remove-button"
        type="button"
        :aria-label="`Remove ${props.filterDefinitions[filterId]!.title} filter`"
        @click="() => emit('remove-filter', filterId)"
      >
        <CmkIcon :aria-label="_t('Remove row')" name="close" size="xxsmall" />
      </button>
    </div>
    <div class="db-filter-selection-collection__item-placeholder">
      {{ _t('Add filter from left panel') }}
    </div>
  </div>
</template>

<style scoped>
.db-filter-selection-collection__container {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.db-filter-selection-collection__item {
  background-color: var(--ux-theme-3);
  padding: var(--dimension-5) var(--dimension-7);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.db-filter-selection-collection__item-title {
  flex: 1;
}

.db-filter-selection-collection__item-remove-button {
  background: none;
  border: none;
  color: var(--color-white-70);
  cursor: pointer;
  font-size: var(--dimension-6);
  font-weight: bold;
  margin-left: var(--dimension-4);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
}

.db-filter-selection-collection__item-placeholder {
  padding: var(--dimension-5) var(--dimension-7);
  border: 1px dashed var(--ux-theme-7);
  color: var(--color-white-70);
}
</style>
