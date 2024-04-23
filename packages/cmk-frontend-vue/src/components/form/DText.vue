<script setup lang="ts">
import { ref, computed, onMounted, onUpdated } from 'vue'
import ValidationError from '@/components/ValidatonError.vue'
import type { VueText } from '@/vue_types'
import { extract_validation, extract_value, type ValueAndValidation } from '@/types'

const emit = defineEmits<{
  (e: 'update-value', value: any): void
}>()

function send_value_upstream(new_value: any) {
  emit('update-value', parseInt(new_value))
}

const props = defineProps<{
  vueSchema: VueText
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
    v-model="component_value"
    :style="style"
    type="text"
    :placeholder="vueSchema.placeholder"
    @input="send_value_upstream(($event!.target! as HTMLInputElement).value)"
  />
  <ValidationError :error="extract_validation(data)"></ValidationError>
</template>
