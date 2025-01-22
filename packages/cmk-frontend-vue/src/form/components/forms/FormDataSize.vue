<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DataSize } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import { useId } from '@/form/utils'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import { computed } from 'vue'

const props = defineProps<{
  spec: DataSize
  backendValidation: ValidationMessages
}>()

const data = defineModel<[string, string]>('data', { required: true })
const [validation, value] = useValidation<[string, string]>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()

const magnitudeOptions = computed(() => {
  return props.spec.displayed_magnitudes.map((element: string) => {
    return {
      name: element,
      title: element
    }
  })
})
</script>

<template>
  <label v-if="props.spec.label" :for="componentId">{{ props.spec.label }}</label>
  <CmkSpace size="small" />
  <input
    :id="componentId"
    v-model="value[0]"
    :placeholder="spec.input_hint || ''"
    class="number no-spinner"
    step="any"
    type="number"
  />
  <CmkSpace size="small" />
  <CmkDropdown
    v-model:selected-option="value[1]"
    :options="magnitudeOptions"
    :show-filter="false"
  />
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.no-spinner::-webkit-outer-spin-button,
.no-spinner::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input.number {
  width: 5.8ex;
}

.no-spinner[type='number'] {
  -moz-appearance: textfield;
}
</style>
