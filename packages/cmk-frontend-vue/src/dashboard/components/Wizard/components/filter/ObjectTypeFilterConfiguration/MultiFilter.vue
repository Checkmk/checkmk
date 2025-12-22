<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import FormButton from '@/form/private/FormButton.vue'

import type { FilterConfigState } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import FilterInputItem from '@/dashboard/components/filter/FilterInputItem/FilterInputItem.vue'
import type { ConfiguredValues } from '@/dashboard/components/filter/types.ts'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

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
      @click="emit('remove-filter', name as string)"
    >
      <CmkIcon :aria-label="_t('Remove filter')" name="close" size="xxsmall" />
    </button>
  </div>
  <div v-if="!inFocus">
    <CmkParagraph style="padding-bottom: var(--dimension-4)">{{
      _t('Add optional filters to refine this widget')
    }}</CmkParagraph>
    <FormButton
      class="db-multi-filter__add-filter-button"
      icon="plus"
      @click="emit('set-focus', objectType)"
      >{{ _t('Add filter') }}</FormButton
    >
  </div>
  <AddFilterMessage v-else />
</template>
<style scoped>
.db-multi-filter__item-container {
  border: var(--ux-theme-8) var(--dimension-1) solid;
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
