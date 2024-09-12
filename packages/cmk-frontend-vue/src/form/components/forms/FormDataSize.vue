<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DataSize } from '@/form/components/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'

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
</script>

<template>
  <label v-if="props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  <input
    :id="$componentId"
    v-model="value[0]"
    :placeholder="spec.input_hint || ''"
    class="number"
    type="text"
  />
  <select v-model="value[1]">
    <option v-for="element in spec.displayed_magnitudes" :key="element" :value="element">
      {{ element }}
    </option>
  </select>
  <FormValidation :validation="validation"></FormValidation>
</template>
