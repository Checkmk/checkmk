<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'

import FilterInputItem from '@/dashboard-wip/components/filter/FilterInputItem/FilterInputItem.vue'
import type { ConfiguredValues, FilterDefinition } from '@/dashboard-wip/components/filter/types.ts'

interface Props {
  filterId: string
  configuredFilterValues: ConfiguredValues | null
  filterDefinitions: Record<string, FilterDefinition>
  allowRemove?: boolean
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

const handleRemoveFilter = () => {
  emit('remove-filter', props.filterId)
}
</script>

<template>
  <div class="filter-collection-item__container">
    <FilterInputItem
      :filter-id="filterId"
      :configured-filter-values="configuredFilterValues"
      @update-filter-values="handleUpdateFilterValues"
    />
    <button
      v-if="allowRemove"
      class="filter-collection-item__container__remove-button"
      :aria-label="`Remove ${props.filterDefinitions[filterId]!.title} filter`"
      @click="handleRemoveFilter"
    >
      <CmkIcon :aria-label="_t('Remove row')" name="close" size="xxsmall" />
    </button>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-collection-item__container {
  padding: var(--dimension-7);
  position: relative;
  display: block;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-collection-item__container__remove-button {
  position: absolute;
  top: 0;
  right: 0;
  background: none;
  border: none;
  color: var(--font-color);
  cursor: pointer;
  font-size: var(--font-size-large);
  font-weight: bold;
  width: var(--dimension-5);
  height: var(--dimension-5);
}
</style>
