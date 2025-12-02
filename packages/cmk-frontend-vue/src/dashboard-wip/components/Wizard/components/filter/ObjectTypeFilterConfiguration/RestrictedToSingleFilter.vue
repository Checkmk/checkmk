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

import FilterInputComponentRenderer from '@/dashboard-wip/components/filter/FilterInputItem/components/FilterInputComponent.vue'
import type { ComponentConfig, ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'
import { useVisualInfoCollection } from '@/dashboard-wip/composables/api/useVisualInfoCollection.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import { getStrings } from '../utils'

const { _t } = usei18n()

const props = defineProps<{
  objectType: ObjectType
}>()

const { filterName } = getStrings(props.objectType)

const configuredFilterValues = defineModel<ConfiguredValues | null>('configuredFilterValues', {
  default: null
})

const { byId, ensureLoaded } = useVisualInfoCollection()

const components = computed((): ComponentConfig[] => {
  const visualInfo = byId.value[props.objectType]
  if (!visualInfo) {
    return []
  }
  return visualInfo.extensions!.single_filter
})

const showFilter = ref<boolean>(configuredFilterValues.value !== null)

const handleComponentChange = (_componentId: string, values: ConfiguredValues): void => {
  configuredFilterValues.value = {
    ...(configuredFilterValues.value ?? {}),
    ...values
  }
}

const handleShowInputs = (): void => {
  showFilter.value = true
}

const handleClear = (): void => {
  if (configuredFilterValues.value === null) {
    return
  }

  delete configuredFilterValues.value[props.objectType]
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
