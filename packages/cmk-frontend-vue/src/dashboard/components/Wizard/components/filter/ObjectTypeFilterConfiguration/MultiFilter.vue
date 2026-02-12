<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import FormButton from '@/form/private/FormButton.vue'

import type { FilterConfigState } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import FilterInputItem from '@/dashboard/components/filter/FilterInputItem/FilterInputItem.vue'
import AddFilterMessage from '@/dashboard/components/filter/shared/AddFilterMessage.vue'
import RemoveFilterButton from '@/dashboard/components/filter/shared/RemoveFilterButton.vue'
import type { ConfiguredValues } from '@/dashboard/components/filter/types.ts'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

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
  <div class="db-multi-filter__list-container">
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
      <RemoveFilterButton
        class="db-multi-filter__remove-button"
        :filter-name="filterDefinitions[name]!.title || ''"
        @remove="emit('remove-filter', name as string)"
      />
    </div>
    <div v-if="!inFocus" class="db-multi-filter__add-button">
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
  </div>
</template>
<style scoped>
.db-multi-filter__item-container {
  background-color: var(--ux-theme-3);
  padding: var(--dimension-7);
  position: relative;
  display: block;
}

.db-multi-filter__remove-button {
  position: absolute;
  top: var(--dimension-4);
  right: var(--dimension-4);
}

.db-multi-filter__list-container {
  gap: var(--dimension-4);
  display: flex;
  flex-direction: column;
}
</style>
