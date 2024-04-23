<script setup lang="ts">
import CmkFormInteger from './element/CmkFormInteger.vue'
import CmkFormFloat from './element/CmkFormFloat.vue'
import CmkFormDictionary from './container/CmkFormDictionary.vue'
import CmkFormText from './element/CmkFormText.vue'
import CmkFormLegacyValueSpec from './element/CmkFormLegacyValueSpec.vue'

import { onBeforeMount, onMounted } from 'vue'
import type { ValueAndValidation } from '@/types'
import type { VueSchema } from '@/vue_types'

const emit = defineEmits<{
  (e: 'update-value', value: unknown): void
}>()

onBeforeMount(() => {
  // console.log('DFORM before mount', props.schema, props.data)
})

onMounted(() => {
  // console.log('DFORM mounted', props.schema, props.data)
})

const props = defineProps<{
  vueSchema: VueSchema
  data: ValueAndValidation<unknown>
}>()

// TODO: https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: Record<string, unknown> = {
  integer: CmkFormInteger,
  float: CmkFormFloat,
  text: CmkFormText,
  dictionary: CmkFormDictionary,
  legacy_valuespec: CmkFormLegacyValueSpec
}

// TODO: we should enforce an interface as return value?!
function get_component(): unknown {
  console.log('get schema ', props.vueSchema)
  console.log('get data   ', props.data)
  return components[props.vueSchema.vue_type!]
}

function forward_value_upstream(new_value: unknown) {
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
