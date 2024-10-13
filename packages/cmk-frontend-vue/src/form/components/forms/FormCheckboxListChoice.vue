<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useValidation, type ValidationMessages } from '../utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import type {
  CheckboxListChoice,
  MultipleChoiceElement
} from '@/form/components/vue_formspec_components'
import { useId } from '@/form/utils'

const props = defineProps<{
  spec: CheckboxListChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<string[]>('data', { required: true })
const [validation, value] = useValidation<string[]>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

function addSelected(element: MultipleChoiceElement) {
  value.value = [...value.value, element.name]
}

function removeSelected(element: MultipleChoiceElement) {
  value.value = value.value.filter((entry) => entry !== element.name)
}

const componentId = useId()
</script>

<template>
  <div v-for="element in props.spec.elements" :key="element.name" class="container">
    <input
      :id="`${componentId}_${element.name}`"
      :checked="value.includes(element.name)"
      type="checkbox"
      @change="value.includes(element.name) ? removeSelected(element) : addSelected(element)"
    />
    <label :for="`${componentId}_${element.name}`">{{ element.title }}</label>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.container {
  padding-bottom: 8px;
}
[type='checkbox'] + label::before {
  border-radius: 2px;
}
</style>
