<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TimePicker } from 'cmk-shared-typing/typescript/vue_formspec_components'

import useId from '@/lib/useId'

import CmkTimePicker from '@/components/CmkDateTimePicker/CmkTimePicker.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import FormLabel from '@/form/private/FormLabel.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import { type ValidationMessages, useValidation } from '@/form/private/validation'

const props = defineProps<{
  spec: TimePicker
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
  <div class="form-time-picker__validation-wrapper">
    <div class="form-time-picker__label">
      <template v-if="props.spec.label">
        <FormLabel :for="componentId"
          >{{ props.spec.label }}
          <CmkSpace size="small" />
        </FormLabel>
        <FormRequired :spec="props.spec" :space="'after'" />
      </template>
    </div>
    <div class="form-time-picker__input-wrapper">
      <FormValidation :validation="validation" />
      <CmkTimePicker :id="componentId" v-model="value" />
    </div>
  </div>
</template>
<style scoped>
.form-time-picker__validation-wrapper {
  display: flex;
  flex-direction: row;
}

.form-time-picker__label {
  display: flex;
  align-items: flex-end;
}

.form-time-picker__input-wrapper {
  display: flex;
  flex-direction: column;
}
</style>
