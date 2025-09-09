<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from '@/components/CmkLabel.vue'

import type { CheckboxGroupConfig, ConfiguredValues } from '../../types.ts'
import CheckboxComponent from './CheckboxComponent.vue'
import type { ComponentEmits } from './types.ts'

export interface CheckboxGroupProps {
  component: CheckboxGroupConfig
  configuredValues: ConfiguredValues | null
}

defineProps<CheckboxGroupProps>()
const emit = defineEmits<ComponentEmits>()

const handleCheckboxChange = (componentId: string, values: ConfiguredValues): void => {
  emit('update-component-values', componentId, values)
}
</script>

<template>
  <fieldset class="checkbox-group">
    <CmkLabel v-if="component.label" variant="subtitle">
      {{ component.label }}
    </CmkLabel>
    <div class="checkbox-group-items">
      <CheckboxComponent
        v-for="[choiceId, choiceLabel] in Object.entries(component.choices)"
        :key="choiceId"
        :component="{
          id: choiceId,
          label: choiceLabel,
          component_type: 'checkbox',
          default_value: false
        }"
        :configured-values="configuredValues"
        @update-component-values="handleCheckboxChange"
      />
    </div>
  </fieldset>
</template>

<style scoped>
.checkbox-group {
  border: none;
  padding: 0;
  margin: 0;
}

.checkbox-group-items {
  display: flex;
  align-items: center;
  gap: var(--dimension-6);
}
</style>
