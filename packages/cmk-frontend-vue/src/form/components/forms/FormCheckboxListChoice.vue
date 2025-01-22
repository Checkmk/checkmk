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
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkCheckbox from '@/components/CmkCheckbox.vue'

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

function change(element: MultipleChoiceElement, newValue: boolean) {
  if (newValue) {
    value.value = [...value.value, element.name]
  } else {
    value.value = value.value.filter((entry) => entry !== element.name)
  }
}
</script>

<template>
  <div>
    <div v-for="element in props.spec.elements" :key="element.name" class="container">
      <CmkCheckbox
        :label="element.title"
        :model-value="value.includes(element.name)"
        @update:model-value="(newValue) => change(element, newValue)"
      />
    </div>
  </div>

  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
div.container:not(:last-of-type) {
  padding-bottom: 8px;
}
</style>
