<script setup lang="ts">
import DInteger from './DInteger.vue'
import DFloat from './DFloat.vue'
import DDictionary from './DDictionary.vue'
import DText from './DText.vue'
import DLegacyValueSpec from './DLegacyValueSpec.vue'

import { onBeforeMount, onMounted } from 'vue'
import type { ValueAndValidation } from '@/types'
import type { VueSchema } from '@/vue_types'

const emit = defineEmits<{
  (e: 'update-value', value: any): void
}>()

onBeforeMount(() => {
  // console.log('DFORM before mount', props.schema, props.data)
})

onMounted(() => {
  // console.log('DFORM mounted', props.schema, props.data)
})

const props = defineProps<{
  vueSchema: VueSchema
  data: ValueAndValidation
}>()

// https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: { [name: string]: {} } = {
  integer: DInteger,
  float: DFloat,
  text: DText,
  // list: DList,
  // list_of: DListOf,
  dictionary: DDictionary,
  legacy_valuespec: DLegacyValueSpec
  // checkbox: DCheckbox,
  // dropdown_choice: DDropdownChoice,
  // cascading_dropdown_choice: DCascadingDropdownChoice,
}

function get_component(): object {
  console.log('get schema ', props.vueSchema)
  console.log('get data   ', props.data)
  return components[props.vueSchema.vue_type!]
}

function forward_value_upstream(new_value: any) {
  // console.log('forward value', props.schema.schema_type, new_value)
  emit('update-value', new_value)
}
</script>

<template>
  <component
    :is="get_component()"
    :vue-schema="vueSchema"
    :data="data"
    @update-value="forward_value_upstream"
  >
  </component>
</template>
