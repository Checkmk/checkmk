<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SingleChoice, SingleChoiceElement } from '@/form/components/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import { useId } from '@/form/utils'
import { computed } from 'vue'
import DropDown from '@/components/DropDown.vue'

const props = defineProps<{
  spec: SingleChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<string | null>('data', { required: true })
const [validation, value] = useValidation<string | null>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()

const options = computed(() => {
  return props.spec.elements.map((element: SingleChoiceElement) => {
    return {
      ident: element.name,
      name: element.title
    }
  })
})
</script>

<template>
  <div>
    <label v-if="$props.spec.label" :for="componentId">{{ spec.label }}</label>
    <DropDown
      v-model:selected-option="value"
      :options="options"
      :input_hint="spec.input_hint"
      :disabled="spec.frozen"
      :component-id="componentId"
    />
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>
