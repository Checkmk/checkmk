<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FixedValue } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import CmkHtml from '@/components/CmkHtml.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import FormLabel from '@/form/private/FormLabel.vue'
import { type ValidationMessages, useValidation } from '@/form/private/validation'

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
  <FormValidation v-if="fixedValue" :validation="validation"></FormValidation>
  <FormLabel v-if="fixedValue">
    <CmkHtml v-if="spec.label" :html="spec.label" />
    <template v-else>{{ fixedValue }}</template>
  </FormLabel>
</template>
