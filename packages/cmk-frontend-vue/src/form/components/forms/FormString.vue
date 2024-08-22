<script setup lang="ts">
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
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

const getSize = (spec: FormSpec.StringFieldSize | undefined): number => {
  return {
    SMALL: 7,
    MEDIUM: 35,
    LARGE: 100
  }[spec || 'MEDIUM']
}
</script>

<template>
  <input
    :id="$componentId"
    v-model="value"
    :placeholder="spec.input_hint || ''"
    type="text"
    :size="getSize(spec.field_size)"
  />
  <FormValidation :validation="validation"></FormValidation>
</template>
