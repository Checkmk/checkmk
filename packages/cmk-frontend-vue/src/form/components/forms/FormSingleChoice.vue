<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SingleChoice } from '@/form/components/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import { useId } from '@/form/utils'

const props = defineProps<{
  spec: SingleChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })
const [validation, value] = useValidation<string>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <div>
    <label v-if="$props.spec.label" :for="componentId">{{ spec.label }}</label>
    <select :id="componentId" v-model="value" :disabled="spec.frozen">
      <option v-if="value.length == 0" disabled selected hidden value="">
        {{ props.spec.input_hint }}
      </option>
      <option
        v-for="element in spec.elements"
        :key="JSON.stringify(element.name)"
        :value="element.name"
      >
        {{ element.title }}
      </option>
    </select>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>
