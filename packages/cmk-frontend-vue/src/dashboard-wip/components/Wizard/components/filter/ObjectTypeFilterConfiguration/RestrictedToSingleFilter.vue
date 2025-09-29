<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import FilterInputComponentRenderer from '@/dashboard-wip/components/filter/FilterInputItem/components/FilterInputComponent.vue'
import type { ComponentConfig, ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'
import { useVisualInfoCollection } from '@/dashboard-wip/composables/api/useVisualInfoCollection.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

const { _t } = usei18n()

const props = defineProps<{
  objectType: ObjectType
}>()

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

onMounted(async () => {
  await ensureLoaded()
  if (byId.value[props.objectType] === undefined) {
    throw new Error(`No visual info found for object type ${props.objectType}`)
  }
})
</script>

<template>
  <div>
    <ActionButton
      v-if="!showFilter"
      :label="_t('Add filter')"
      :icon="{ name: 'plus', side: 'left' }"
      variant="secondary"
      :action="handleShowInputs"
    />

    <div v-else>
      <FilterInputComponentRenderer
        v-for="component in components"
        :key="`${'id' in component ? component.id : component.component_type}`"
        :component="component"
        :configured-filter-values="configuredFilterValues"
        @update-component-values="handleComponentChange"
      />
    </div>
  </div>
</template>
