<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'
import type { DualListElement } from '@/components/CmkDualList/index.ts'

import type { ConfiguredValues, DualListConfig } from '../../types.ts'
import type { ComponentEmits } from './types.ts'

interface Props {
  component: DualListConfig
  configuredValues: ConfiguredValues | null
}

const props = defineProps<Props>()
const emit = defineEmits<ComponentEmits>()

const updateComponentValues = (componentId: string, values: Record<string, string>): void => {
  emit('update-component-values', componentId, values)
}

if (props.configuredValues === null) {
  updateComponentValues(props.component.id, { [props.component.id]: '' })
}

const dualListElements = computed<DualListElement[]>(() => {
  if (!props.component.choices) {
    return []
  }
  return Object.entries(props.component.choices).map(([name, title]) => ({
    name,
    title
  }))
})

const selectedDualListElements = computed<DualListElement[]>({
  get() {
    const selectedValues = props.configuredValues?.[props.component.id]
    if (selectedValues) {
      const selectedNames = selectedValues.split('|')
      return dualListElements.value.filter((el) => selectedNames.includes(el.name))
    }
    return []
  },
  set(newValues: DualListElement[]) {
    const valuesString = newValues.map((el) => el.name).join('|')
    updateComponentValues(props.component.id, { [props.component.id]: valuesString })
  }
})
</script>

<template>
  <CmkDualList
    v-if="component.choices"
    v-model:data="selectedDualListElements"
    :elements="dualListElements"
    :title="component.id"
    :validators="[]"
    :backend-validation="[]"
  />
</template>
