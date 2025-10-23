<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'

import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import type { FilterConfigState } from '@/dashboard-wip/components/Wizard/components/filter/utils.ts'
import FilterInputItem from '@/dashboard-wip/components/filter/FilterInputItem/FilterInputItem.vue'
import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'
import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import AddFilterMessage from './AddFilterMessage.vue'

interface Props {
  objectType: ObjectType
  objectConfiguredFilters: FilterConfigState
  inFocus: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'remove-filter', filterId: string): void
}>()

const { _t } = usei18n()

const filterDefinitions = useFilterDefinitions()

const handleRemoveFilter = (filterId: string) => {
  emit('remove-filter', filterId)
}
</script>

<template>
  <div
    v-for="(configuredValues, name) in objectConfiguredFilters"
    :key="name as string"
    class="db-multi-filter__item-container"
  >
    <FilterInputItem
      :filter-id="name as string"
      :configured-filter-values="configuredValues"
      @update-filter-values="
        (id: string, values: ConfiguredValues) => emit('update-filter-values', id, values)
      "
    />
    <button
      class="db-multi-filter__remove-button"
      :aria-label="`Remove ${filterDefinitions[name]!.title} filter`"
      @click="handleRemoveFilter(name as string)"
    >
      <CmkIcon :aria-label="_t('Remove row')" name="close" size="xxsmall" />
    </button>
  </div>
  <ActionButton
    v-if="!inFocus"
    :label="_t('Add filter')"
    :icon="{ name: 'plus', side: 'left' }"
    variant="secondary"
    :action="
      () => {
        emit('set-focus', objectType)
      }
    "
  />
  <AddFilterMessage v-else />
</template>
<style scoped>
.db-multi-filter__item-container {
  border: var(--ux-theme-8) 1px dashed;
  margin: var(--spacing);
  padding: var(--spacing-double);
  position: relative;
  display: block;
}

.db-multi-filter__remove-button {
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
