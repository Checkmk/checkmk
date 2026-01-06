<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkIcon from '@/components/CmkIcon'

import FilterInputItem from '@/dashboard/components/filter/FilterInputItem/FilterInputItem.vue'
import type { ConfiguredValues, FilterDefinition } from '@/dashboard/components/filter/types.ts'

interface Props {
  filterId: string
  configuredFilterValues: ConfiguredValues | null
  filterDefinitions: Record<string, FilterDefinition>
  allowRemove?: boolean
  showRequiredLabel?: boolean
  label?: TranslatedString | undefined
}

interface Emits {
  'update-filter-values': [filterId: string, values: ConfiguredValues]
  'remove-filter': [filterId: string]
}

const { _t } = usei18n()
const props = withDefaults(defineProps<Props>(), {
  allowRemove: true
})
const emit = defineEmits<Emits>()

const handleUpdateFilterValues = (filterId: string, values: ConfiguredValues) => {
  emit('update-filter-values', filterId, values)
}
</script>

<template>
  <div class="db-filter-collection-input-item__container">
    <FilterInputItem
      :filter-id="filterId"
      :configured-filter-values="configuredFilterValues"
      :show-required-label="showRequiredLabel"
      @update-filter-values="handleUpdateFilterValues"
    />
    <div v-if="allowRemove || label" class="db-filter-collection-input-item__actions">
      <span v-if="label" class="db-filter-collection-input-item__label">{{ label }}</span>
      <button
        v-if="allowRemove"
        class="db-filter-collection-input-item__remove-button"
        :aria-label="`Remove ${props.filterDefinitions[filterId]!.title} filter`"
        @click="emit('remove-filter', props.filterId)"
      >
        <CmkIcon :aria-label="_t('Remove row')" name="close" size="xxsmall" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.db-filter-collection-input-item__container {
  padding: var(--dimension-7);
  position: relative;
  display: block;
}

.db-filter-collection-input-item__actions {
  position: absolute;
  top: var(--dimension-4);
  right: var(--dimension-4);
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
}

.db-filter-collection-input-item__label {
  padding: var(--dimension-2) var(--dimension-3);
  border-radius: var(--border-radius-half);
  background-color: var(--ux-theme-7);
  font-size: var(--font-size-small);
}

.db-filter-collection-input-item__remove-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-6);
  height: var(--dimension-6);
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  color: var(--font-color);
  cursor: pointer;
  font-size: var(--font-size-large);
  font-weight: bold;
}
</style>
