<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import type { TextInputConfig } from '../../types.ts'
import type { ComponentEmits, FilterComponentProps } from './types.ts'

const props = defineProps<FilterComponentProps<TextInputConfig>>()
const emit = defineEmits<ComponentEmits>()

const getInitialValue = (): string => {
  return props.configuredValues?.[props.component.id] ?? ''
}

const currentValue = ref(getInitialValue())

if (props.configuredValues === null) {
  emit('update-component-values', props.component.id, { [props.component.id]: currentValue.value })
}

watch(currentValue, (newValue) => {
  emit('update-component-values', props.component.id, { [props.component.id]: newValue })
})
</script>

<template>
  <div class="text-input-group">
    <div>
      <CmkLabel v-if="component.label" :for="component.id">
        {{ component.label }}
      </CmkLabel>
    </div>
    <CmkInput
      v-model="currentValue"
      type="text"
      :unit="component.suffix || ''"
      field-size="SMALL"
    />
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.text-input-group {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
