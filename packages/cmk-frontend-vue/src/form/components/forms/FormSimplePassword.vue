<script setup lang="ts">
import FormValidation from '@/form/components/FormValidation.vue'
import { validateValue, type ValidationMessages } from '@/form/components/utils/validation'
import { computed, ref } from 'vue'
import type { SimplePassword } from '@/form/components/vue_formspec_components'
import { immediateWatch } from '@/form/components/utils/watch'

const props = defineProps<{
  spec: SimplePassword
  backendValidation: ValidationMessages
}>()

const data = defineModel<[string, boolean]>('data', { required: true })

const validation = ref<Array<string>>([])

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    validation.value = newValidation.map((vm) => vm.message)
  }
)
const password = computed({
  get: () => (data.value[1] ? '' : data.value[0]),
  set: (value: string) => {
    validation.value = validateValue(value, props.spec.validators)
    data.value[0] = value
    data.value[1] = false
  }
})
</script>

<template>
  <input :id="$componentId" v-model="password" type="password" :placeholder="'******'" />
  <label :for="$componentId" />
  <FormValidation :validation="validation"></FormValidation>
</template>
