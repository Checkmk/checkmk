<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import FormLabel from '@/form/private/FormLabel.vue'

const props = defineProps<{
  spec: FormSpec.MultilineText
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })
const [validation, value] = useValidation<string>(
  data,
  props.spec.validators,
  () => props.backendValidation
)
const style = computed(() => {
  return props.spec.monospaced
    ? {
        'font-family': 'monospace, sans-serif'
      }
    : {}
})
</script>

<template>
  <div style="flex">
    <div v-if="spec.label">
      <FormLabel> {{ spec.label }}</FormLabel
      ><br />
    </div>
    <textarea
      v-model="value"
      :style="style"
      :placeholder="spec.input_hint || ''"
      :aria-label="spec.label || spec.title"
      rows="4"
      cols="60"
      type="text"
    />
    <FormValidation :validation="validation"></FormValidation>
  </div>
</template>
