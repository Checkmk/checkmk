<script setup lang="ts">
import { computed } from 'vue'
import { FormValidation } from '@/components/cmk-form/'
import type * as FormSpec from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'
import { type ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: FormSpec.MultilineText
  backendValidation: ValidationMessages
}>()

const data = defineModel('data', { type: String, required: true })
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
  <div v-if="props.spec.label">
    <label> {{ props.spec.label }}</label
    ><br />
  </div>
  <textarea
    v-model="value"
    :style="style"
    :placeholder="spec.input_hint || ''"
    rows="20"
    cols="60"
    type="text"
  />
  <FormValidation :validation="validation"></FormValidation>
</template>
