<script setup lang="ts">
import { ref, computed, onMounted, onUpdated } from 'vue'
import ValidationError from '@/components/ValidatonError.vue'
import type { VueSchema, VueText } from '@/vue_types'
import { extract_validation, extract_value, type ValueAndValidation } from '@/types'

const emit = defineEmits<{
  (e: 'update-value', value: any): void
}>()

function send_value_upstream(new_value: any) {
  emit('update-value', parseInt(new_value))
}

const props = defineProps<{
  vue_schema: VueText
  data: ValueAndValidation
}>()

const component_value = ref<string>()

onMounted(() => {
  // console.log("mounted text")
  component_value.value = extract_value(props.data)
  send_value_upstream(component_value.value)
})

onUpdated(() => {
  console.log('updated text')
})

let style = computed(() => {
  return { width: '25.8ex' }
})
</script>

<template>
  <input
    :style="style"
    type="text"
    v-model="component_value"
    @input="send_value_upstream(($event!.target! as HTMLInputElement).value)"
    :placeholder="vue_schema.placeholder"
  />
  <ValidationError :error="extract_validation(data)"></ValidationError>
</template>
