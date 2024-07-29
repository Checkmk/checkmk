<script setup lang="ts">
import { FormValidation } from '@/components/cmk-form/'
import type { LegacyValuespec } from '@/vue_formspec_components'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { select } from 'd3-selection'
import type { ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: LegacyValuespec
  backendValidation: ValidationMessages
}>()

const validation = ref<ValidationMessages>([])

watch(
  () => props.backendValidation,
  (new_validation: ValidationMessages) => {
    const validations: ValidationMessages = []
    new_validation.forEach((message) => {
      validations.push({
        location: [],
        message: message.message,
        invalid_value: message.invalid_value
      })
    })
    validation.value = validations
  },
  { immediate: true }
)

defineModel<unknown>('data', { required: true })
const legacyDOM = ref<HTMLFormElement>()

onMounted(() => {
  select(legacyDOM.value!).selectAll('input,select').on('input.observer', collect_data)
  collect_data()
})

onBeforeUnmount(() => {
  select(legacyDOM.value!).selectAll('input').on('input.observer', null)
})

function collect_data() {
  let result = Object.fromEntries(new FormData(legacyDOM.value))
  emit('update:data', {
    input_context: result,
    varprefix: props.spec.varprefix
  })
}

const emit = defineEmits<{
  (e: 'update:data', value: unknown): void
}>()
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <form
    ref="legacyDOM"
    style="background: #595959"
    class="legacy_valuespec"
    v-html="spec.input_html"
  ></form>
  <!--eslint-enable-->
  <FormValidation :validation="validation"></FormValidation>
</template>
