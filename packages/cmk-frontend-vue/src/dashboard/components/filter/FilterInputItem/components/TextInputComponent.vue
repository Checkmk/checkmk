<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

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

const decodedLabel = computed(() => props.component.label?.replace(/&nbsp;/g, '\u00A0') ?? '')
</script>

<template>
  <div class="db-text-input-component">
    <div>
      <CmkLabel v-if="component.label" :for="component.id">
        {{ decodedLabel }}
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
.db-text-input-component {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
