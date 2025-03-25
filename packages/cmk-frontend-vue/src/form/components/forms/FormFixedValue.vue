<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import { computed } from 'vue'
import type { FixedValue } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'
import FormLabel from '@/form/private/FormLabel.vue'

const props = defineProps<{
  spec: FixedValue
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })
const [validation] = useValidation<unknown>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const fixedValue = computed(() => {
  return props.spec.label === null ? props.spec.value : props.spec.label
})
</script>

<template>
  <FormLabel v-if="fixedValue">{{ fixedValue }}</FormLabel>
  <FormValidation v-if="fixedValue" :validation="validation"></FormValidation>
</template>
