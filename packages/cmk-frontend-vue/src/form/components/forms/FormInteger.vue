<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Integer } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import CmkSpace from '@/components/CmkSpace.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import FormValidation from '@/form/components/FormValidation.vue'
import { useId } from '@/form/utils'

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

const componentId = useId()
</script>

<template>
  <template v-if="props.spec.label">
    <label :for="componentId">{{ props.spec.label }}<CmkSpace size="small" /> </label>
    <FormRequired
      :spec="props.spec"
      :i18n-required="props.spec.i18n_base.required"
      :space="'after'"
    />
  </template>
  <input
    :id="componentId"
    v-model="value"
    :placeholder="spec.input_hint || ''"
    class="number no-spinner"
    step="any"
    type="number"
  />
  <span v-if="spec.unit" class="vs_floating_text"><CmkSpace size="small" />{{ spec.unit }}</span>
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
