<script setup lang="ts">
import { type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import type { LegacyValuespec } from '@/vue_formspec_components'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { select } from 'd3-selection'

const props = defineProps<{
  spec: LegacyValuespec
  validation: ValidationMessages
}>()

defineModel<unknown>('data', { required: true })
const legacy_dom = ref<HTMLFormElement>()

onMounted(() => {
  select(legacy_dom.value!).selectAll('input,select').on('input.observer', collect_data)
  collect_data()
})

onBeforeUnmount(() => {
  select(legacy_dom.value!).selectAll('input').on('input.observer', null)
})

function collect_data() {
  let result = Object.fromEntries(new FormData(legacy_dom.value))
  emit('update:data', {
    input_context: result,
    varprefix: props.spec.varprefix
  })
}

const emit = defineEmits<{
  (e: 'update:data', value: unknown): void
}>()

const remaining_validations = computed(() => {
  const messages: ValidationMessages = []
  props.validation.forEach((msg) => {
    messages.push({
      location: [],
      message: msg.message
    })
  })
  return messages
})
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <form
    ref="legacy_dom"
    style="background: #595959"
    class="legacy_valuespec"
    v-html="spec.html"
  ></form>
  <!--eslint-enable-->
  <FormValidation :validation="remaining_validations"></FormValidation>
</template>
