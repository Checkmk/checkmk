<script setup lang="ts">
import { FormValidation } from '@/components/cmk-form/'
import type { Float } from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'
import { type ValidationMessages } from '@/lib/validation'

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
</script>

<template>
  <label v-if="props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  <input
    :id="$componentId"
    v-model="value"
    :placeholder="spec.input_hint || ''"
    class="number"
    type="number"
  />
  <span v-if="props.spec.unit" class="vs_floating_text">{{ props.spec.unit }}</span>
  <FormValidation :validation="validation"></FormValidation>
</template>
