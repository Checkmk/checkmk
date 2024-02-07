<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { VueComponentSpec } from '@/types'
import ValidationError from '../ValidatonError.vue'

interface VuePercentageComponentSpec extends VueComponentSpec {
  config: {
    value: number
  }
}

const props = defineProps<{
  component: VuePercentageComponentSpec
}>()

const component_value = ref<string>()

onMounted(() => {
  component_value.value = props.component.config.value.toString()
})

let style = computed(() => {
  return { width: '5.8ex' }
})

function collect(): number {
  if (component_value.value == null)
    // TODO: may throw "required" exception, and blocks sending of form
    return 0
  return parseInt(component_value.value)
}

function debug_info() {
  console.log('Number input', props.component.title)
}

defineExpose({
  collect,
  debug_info
})
</script>

<template>
  <!--  <div>{{component}}</div>-->
  <input class="number" :style="style" type="text" v-model="component_value" />
  <span class="vs_floating_text">%</span>
  <ValidationError :component="component"></ValidationError>
</template>
