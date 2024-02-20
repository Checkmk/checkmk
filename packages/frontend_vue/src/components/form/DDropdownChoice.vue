<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { VueComponentSpec } from '@/types'
import ValidationError from '../ValidatonError.vue'

interface VueDropdownChoiceComponentSpec extends VueComponentSpec {
  config: {
    value: string
    elements: [string, string][]
  }
}

const props = defineProps<{
  component: VueDropdownChoiceComponentSpec
}>()

const selected = ref('')

onMounted(() => {
  console.log('DropdownChoice mounted', props)
  selected.value = props.component.config.value
  send_value_upstream(selected.value)
})

const emit = defineEmits<{
  (e: 'update-value', value: any): void
}>()

function send_value_upstream(new_value: string) {
  emit('update-value', new_value)
}
</script>
<template>
  <div>
    <select v-model="selected" @change="send_value_upstream($event.target.value)">
      <option :value="element[0]" v-for="element in component.config.elements">
        {{ element[1] }}
      </option>
    </select>
  </div>
</template>
