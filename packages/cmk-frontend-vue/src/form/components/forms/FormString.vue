<script setup lang="ts">
import type * as FormSpec from '@/vue_formspec_components'
import { useValidation } from '@/form/components/utils/validation'
import { type ValidationMessages } from '@/lib/validation'
import FormValidation from '@/form/components/FormValidation.vue'

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
  <input :id="$componentId" v-model="value" :placeholder="spec.input_hint || ''" type="text" />
  <FormValidation :validation="validation"></FormValidation>
</template>
