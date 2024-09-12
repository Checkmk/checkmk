<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import { computed } from 'vue'
import type { FixedValue } from '@/form/components/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'

const props = defineProps<{
  spec: FixedValue
  backendValidation: ValidationMessages
}>()

const data = defineModel<number | string | boolean>('data', { required: true })
const [validation, _value] = useValidation<number | string | boolean>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const fixedValue = computed(() => {
  return props.spec.label || props.spec.value
})
</script>

<template>
  <label>{{ fixedValue }}</label>
  <FormValidation :validation="validation"></FormValidation>
</template>
