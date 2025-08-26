<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Float } from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkSpace from '@/components/CmkSpace.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import { type ValidationMessages, useValidation } from '@/form/components/utils/validation'
import FormLabel from '@/form/private/FormLabel.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import { useId } from '@/form/utils'

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
  <template v-if="props.spec.label">
    <FormLabel :for="componentId">{{ props.spec.label }}<CmkSpace size="small" /> </FormLabel>
    <FormRequired :spec="props.spec" :space="'after'" />
  </template>
  <CmkInput
    :id="componentId"
    v-model="value"
    :type="'number'"
    :placeholder="props.spec.input_hint || ''"
    :aria-label="props.spec.label || props.spec.title"
    :external-errors="validation"
  />
</template>
