<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
// import DList from './DList.vue'
import DInteger from './DInteger.vue'
import DFloat from './DFloat.vue'
import DDictionary from './DDictionary.vue'
import DText from './DText.vue'
import DLegacyValueSpec from './DLegacyValueSpec.vue'

import { onBeforeMount, onMounted } from 'vue'
import type { ValueAndValidation } from '@/types'
import type { VueSchema } from '@/vue_types'
// import DDropdownChoice from "cmk_vue/components/form/DDropdownChoice.vue";
// import DCheckbox from "cmk_vue/components/form/DCheckbox.vue";
// import DCascadingDropdownChoice from "cmk_vue/components/form/DCascadingDropdownChoice.vue";
// import DPercentage from '@/components/form/DPercentage.vue'
// import DListOf from "cmk_vue/components/form/DListOf.vue";

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
  vue_schema: VueSchema
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
  console.log('get schema ', props.vue_schema)
  console.log('get data   ', props.data)
  return components[props.vue_schema.vue_type!]
}

function forward_value_upstream(new_value: any) {
  // console.log('forward value', props.schema.schema_type, new_value)
  emit('update-value', new_value)
}
</script>

<template>
  <component
    v-bind:is="get_component()"
    :vue_schema="vue_schema"
    :data="data"
    @update-value="forward_value_upstream"
  >
  </component>
</template>
