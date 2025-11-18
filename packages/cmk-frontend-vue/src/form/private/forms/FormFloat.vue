<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Float } from 'cmk-shared-typing/typescript/vue_formspec_components'

import useId from '@/lib/useId'

import CmkSpace from '@/components/CmkSpace.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FormLabel from '@/form/private/FormLabel.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import { type ValidationMessages, useValidation } from '@/form/private/validation'

const props = defineProps<{
  spec: Float
  backendValidation: ValidationMessages
}>()

const data = defineModel<number>('data', { required: true })
const [validation, value] = useValidation<number>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <div class="form-float__validation-wrapper">
    <div class="form-float__label">
      <template v-if="props.spec.label">
        <FormLabel :for="componentId">{{ props.spec.label }}<CmkSpace size="small" /> </FormLabel>
        <FormRequired :spec="props.spec" :space="'after'" />
      </template>
    </div>
    <CmkInput
      :id="componentId"
      v-model="value"
      :type="'number'"
      :placeholder="props.spec.input_hint || ''"
      :aria-label="props.spec.label || props.spec.title"
      :external-errors="validation"
      :unit="props.spec.unit || ''"
    />
  </div>
</template>
<style scoped>
.form-float__validation-wrapper {
  display: flex;
  flex-direction: row;
}

.form-float__label {
  display: flex;
  align-items: flex-end;
}
</style>
