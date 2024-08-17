<script setup lang="ts">
import type { LegacyValuespec } from '@/form/components/vue_formspec_components'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { select } from 'd3-selection'
import FormValidation from '@/form/components/FormValidation.vue'
import type { ValidationMessages } from '@/form/components/utils/validation'

const props = defineProps<{
  spec: LegacyValuespec
  backendValidation: ValidationMessages
}>()

const validation = ref<ValidationMessages>([])

watch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const validations: ValidationMessages = []
    newValidation.forEach((message) => {
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

const data = defineModel<unknown>('data', { required: true })
const legacyDOM = ref<HTMLFormElement>()

onMounted(() => {
  select(legacyDOM.value!).selectAll('input,select').on('input.observer', collectData)
  collectData()
})

onBeforeUnmount(() => {
  select(legacyDOM.value!).selectAll('input').on('input.observer', null)
})

function collectData() {
  let result = Object.fromEntries(new FormData(legacyDOM.value))
  data.value = {
    input_context: result,
    varprefix: props.spec.varprefix
  }
}
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
