<script setup lang="ts">
import DForm from './DForm.vue'
import { onMounted, onUpdated, onBeforeUpdate, ref, onBeforeMount } from 'vue'
import { IComponent, VueComponentSpec } from '@/types'

interface VueCascadingDropdownChoiceComponentSpec extends VueComponentSpec {
  config: {
    value: string
    elements: [string, string, VueComponentSpec][]
  }
}

const props = defineProps<{
  component: VueCascadingDropdownChoiceComponentSpec
}>()

const selection_option = ref('')
const active_component = ref({})
const child = ref<IComponent | null>(null)

function debug_info() {
  console.log('Cascading Dropdown', props.component.config)
}

defineExpose({
  collect,
  debug_info
})

function collect() {
  if (!child.value) throw 'Error fetching data from child'
  return [selection_option.value, child.value.collect()]
}

function get_active_component() {
  for (const entry of props.component.config.elements) {
    if (entry[0] == selection_option.value) {
      console.log('active component is ', entry[2])
      return entry[2]
    }
  }
  return props.component.config.elements[0][2]
}

onBeforeMount(() => {
  console.log('on before mount ')
  selection_option.value = props.component.config.value
  active_component.value = get_active_component()
})

onMounted(() => {
  console.log('on mounted')
  selection_option.value = props.component.config.value
  active_component.value = get_active_component()
})

function onChange() {
  // TODO: LoadOnDemand: Fetch component spec
  //       Since this requires authentication and custom pages, we will introduce this
  //       once the code runs natively in checkmk
  active_component.value = get_active_component()
}

onBeforeUpdate(() => {
  console.log('updating cascading')
  active_component.value = get_active_component()
})
</script>

<template>
  <select class="cascading_dropdown" v-model="selection_option" @change="onChange()">
    <option :value="choice[0]" v-for="choice in component.config.elements">
      {{ choice[1] }}
    </option>
  </select>
  <br />
  <DForm :component="active_component" ref="child" />
</template>
