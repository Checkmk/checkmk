<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Integer } from '@/form/components/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'

const props = defineProps<{
  spec: Integer
  backendValidation: ValidationMessages
}>()

const data = defineModel<string | number>('data', { required: true })
const [validation, value] = useValidation<string | number>(
  data,
  props.spec.validators,
  () => props.backendValidation
)
</script>

<template>
  <label v-if="props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  <input
    :id="$componentId"
    v-model="value"
    :placeholder="spec.input_hint || ''"
    class="number no-spinner"
    step="any"
    type="number"
  />
  <span v-if="props.spec.unit" class="vs_floating_text">{{ props.spec.unit }}</span>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.no-spinner::-webkit-outer-spin-button,
.no-spinner::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.no-spinner[type='number'] {
  -moz-appearance: textfield;
}
</style>
