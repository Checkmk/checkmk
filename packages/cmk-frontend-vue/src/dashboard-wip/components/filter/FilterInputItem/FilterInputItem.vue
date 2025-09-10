<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'

import type { ComponentConfig, ConfiguredValues, FilterDefinition } from '../types.ts'
import FilterInputComponentRenderer from './components/FilterInputComponent.vue'
import type { FilterEmits } from './components/types.ts'

interface Props {
  filterId: string
  configuredFilterValues: ConfiguredValues | null
}

const props = defineProps<Props>()
const emit = defineEmits<FilterEmits>()

const filterDefinitions = inject<Record<string, FilterDefinition> | null>('filterDefinitions', null)
if (!filterDefinitions) {
  throw new Error('Filter definitions are not available')
}
const filterDefinition = filterDefinitions[props.filterId]
if (!filterDefinition) {
  throw new Error(`Filter definition for ${props.filterId} not found`)
}

const localConfiguredFilterValues = ref({ ...props.configuredFilterValues })

watch(
  () => props.configuredFilterValues,
  (newValue) => {
    localConfiguredFilterValues.value = { ...newValue }
  }
)

const components = computed((): ComponentConfig[] => {
  return filterDefinition.extensions.components || []
})

const handleComponentChange = (_componentId: string, values: ConfiguredValues): void => {
  const updatedFilterValues: ConfiguredValues = {
    ...localConfiguredFilterValues.value,
    ...values
  }

  localConfiguredFilterValues.value = updatedFilterValues
  emit('update-filter-values', filterDefinition.id!, updatedFilterValues)
}
</script>

<template>
  <div class="filter-container">
    <div class="filter-title">
      {{ filterDefinition.title }}
    </div>
    <div class="filter-components">
      <FilterInputComponentRenderer
        v-for="component in components"
        :key="`${filterDefinition.id} ${'id' in component ? component.id : component.component_type}`"
        :component="component"
        :configured-filter-values="configuredFilterValues"
        @update-component-values="handleComponentChange"
      />
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-title {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
  margin-bottom: var(--dimension-4);
  color: var(--font-color);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-components {
  width: 100%;
  display: flex;
  margin-top: var(--dimension-4);
  flex-direction: column;
  gap: var(--dimension-6);
  justify-content: space-between;
}
</style>
