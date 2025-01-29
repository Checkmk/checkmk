<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SingleChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import { useId } from '@/form/utils'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkSpace from '@/components/CmkSpace.vue'

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
</script>

<template>
  <div>
    <label v-if="$props.spec.label" :for="componentId"
      >{{ spec.label }}<CmkSpace size="small"
    /></label>
    <CmkDropdown
      v-model:selected-option="value"
      :options="props.spec.elements"
      :input-hint="spec.input_hint || ''"
      :disabled="spec.frozen"
      :component-id="componentId"
      :show-filter="props.spec.elements.length > 5"
      :no-elements-text="props.spec.no_elements_text || ''"
      :required-text="props.spec.i18n_base.required"
    />
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>
