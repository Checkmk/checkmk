<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { capitalizeFirstLetter } from '@/lib/utils'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import FormButton from '@/form/private/FormButton.vue'

import FilterInputComponentRenderer from '@/dashboard/components/filter/FilterInputItem/components/FilterInputComponent.vue'
import type { ComponentConfig, ConfiguredValues } from '@/dashboard/components/filter/types.ts'
import { useVisualInfoCollection } from '@/dashboard/composables/api/useVisualInfoCollection.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

import { getStrings } from '../utils'

const { _t } = usei18n()

const props = defineProps<{
  objectType: ObjectType
  configuredFilterValues: ConfiguredValues
}>()

const emit = defineEmits<{
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'remove-filter', filterId: string): void
}>()

const { filterName } = getStrings(props.objectType)

const { byId, ensureLoaded } = useVisualInfoCollection()

const components = computed((): ComponentConfig[] => {
  const visualInfo = byId.value[props.objectType]
  if (!visualInfo) {
    return []
  }
  return visualInfo.extensions!.single_filter
})

const showFilter = ref<boolean>(Object.keys(props.configuredFilterValues).length > 0)

const handleComponentChange = (_componentId: string, values: ConfiguredValues): void => {
  emit('update-filter-values', props.objectType, {
    ...props.configuredFilterValues,
    ...values
  })
}

const handleShowInputs = (): void => {
  showFilter.value = true
}

const handleClear = (): void => {
  emit('remove-filter', props.objectType)
  showFilter.value = false
}

onMounted(async () => {
  await ensureLoaded()
  if (byId.value[props.objectType] === undefined) {
    throw new Error(`No visual info found for object type ${props.objectType}`)
  }
})
</script>

<template>
  <div>
    <div v-if="!showFilter">
      <CmkParagraph style="padding-bottom: var(--dimension-4)">{{
        _t('Add optional filter to refine this widget')
      }}</CmkParagraph>
      <FormButton icon="plus" @click="handleShowInputs">{{
        _t('Add %{name}', { name: filterName })
      }}</FormButton>
    </div>

    <div v-else class="db-restricted-to-single-filter__container">
      <div
        v-for="component in components"
        :key="`${'id' in component ? component.id : component.component_type}`"
      >
        <CmkParagraph class="db-restricted-to-single-filter__filter-title">{{
          capitalizeFirstLetter(filterName)
        }}</CmkParagraph>
        <button
          class="db-restricted-to-single-filter__remove-button"
          :aria-label="`Remove ${filterName} filter`"
          @click="handleClear"
        >
          <CmkIcon :aria-label="_t('Remove filter')" name="close" size="xxsmall" />
        </button>

        <FilterInputComponentRenderer
          :component="component"
          :configured-filter-values="configuredFilterValues"
          @update-component-values="handleComponentChange"
        />
      </div>
    </div>
  </div>
</template>
<style scoped>
.db-restricted-to-single-filter__container {
  border: var(--ux-theme-8) 1px solid;
  margin: var(--spacing);
  padding: var(--spacing-double);
  position: relative;
  display: block;
}

.db-restricted-to-single-filter__filter-title {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
}

.db-restricted-to-single-filter__remove-button {
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
