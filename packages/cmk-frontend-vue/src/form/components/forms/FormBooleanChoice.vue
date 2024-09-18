<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import type { BooleanChoice } from '@/form/components/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import { useId } from '@/form/utils'

const props = defineProps<{
  spec: BooleanChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<boolean>('data', { required: true })
const [validation, value] = useValidation<boolean>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <span class="checkbox">
    <input :id="componentId" v-model="value" type="checkbox" />
    <label :for="componentId">{{ props.spec.label }}</label>
  </span>
  <FormValidation :validation="validation"></FormValidation>
</template>
