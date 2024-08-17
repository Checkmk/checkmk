<script setup lang="ts">
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import type { BooleanChoice } from '@/form/components/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'

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
</script>

<template>
  <span class="checkbox">
    <input :id="$componentId" v-model="value" type="checkbox" />
    <label :for="$componentId">{{ props.spec.label }}</label>
  </span>
  <FormValidation :validation="validation"></FormValidation>
</template>
