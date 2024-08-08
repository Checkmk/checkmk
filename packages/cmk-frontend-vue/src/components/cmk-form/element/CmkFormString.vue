<script setup lang="ts">
import { FormValidation } from '@/components/cmk-form/'
import type * as FormSpec from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'
import { type ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: FormSpec.String
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })
const [validation, value] = useValidation<string>(
  data,
  props.spec.validators,
  () => props.backendValidation
)
</script>

<template>
  <label :for="$componentId">{{ props.spec.title }}</label>
  <input :id="$componentId" v-model="value" :placeholder="spec.input_hint || ''" type="text" />
  <FormValidation :validation="validation"></FormValidation>
</template>
