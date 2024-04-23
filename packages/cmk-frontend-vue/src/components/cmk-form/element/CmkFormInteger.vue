<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { extract_validation, extract_value, type ValueAndValidation } from '@/types'
import ValidationError from '../ValidationError.vue'
import type { VueInteger } from '@/vue_types'

const emit = defineEmits<{
  (e: 'update-value', value: number): void
}>()

const props = defineProps<{
  vueSchema: VueInteger
  data: ValueAndValidation<number>
}>()

const component_value = ref<string>()

onMounted(() => {
  component_value.value = extract_value(props.data).toString()
  send_value_upstream(component_value.value!)
})

function send_value_upstream(new_value: string) {
  emit('update-value', Number(new_value))
}

let unit = computed(() => {
  return props.vueSchema.unit || ''
})

let style = computed(() => {
  return { width: '5.8ex' }
})
</script>

<template>
  <input
    class="number"
    :style="style"
    type="text"
    :value="component_value"
    @input="send_value_upstream(($event!.target! as HTMLInputElement).value)"
  />
  <span v-if="unit" class="vs_floating_text">{{ unit }}</span>
  <ValidationError :error="extract_validation(data)"></ValidationError>
</template>
