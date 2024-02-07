<script setup lang="ts">
import { VueComponentSpec } from '@/types'

import { ref, onMounted, onBeforeMount } from 'vue'
import { clicked_checkbox_label } from '@/utils'

interface VueCheckboxComponentSpec extends VueComponentSpec {
  config: {
    value: boolean
    label: string
  }
}
const props = defineProps<{
  component: VueCheckboxComponentSpec
}>()

const value = ref(true)

onMounted(() => {
  value.value = props.component.config.value
})

const emit = defineEmits<{
  (e: 'update-value', value: any): void
}>()
function send_value_upstream(new_value: string) {
  emit('update-value', parseInt(new_value))
}
</script>
<template>
  <span class="checkbox">
    <input
      class="vue_checkbox"
      type="checkbox"
      v-model="value"
      @input="send_value_upstream(event.target.value)"
    />
    <label :onclick="clicked_checkbox_label">{{ component.config.label }}</label>
  </span>
</template>
