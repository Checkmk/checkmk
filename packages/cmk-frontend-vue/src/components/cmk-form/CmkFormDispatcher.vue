<script setup lang="ts">
import CmkFormInteger from './element/CmkFormInteger.vue'
import CmkFormString from './element/CmkFormString.vue'
import CmkFormDictionary from './container/CmkFormDictionary.vue'
import type { ValidationMessages } from '@/utils'
import type { VueSchema } from '@/vue_formspec_components'

const props = defineProps<{
  spec: VueSchema
  validation: ValidationMessages
}>()

const data = defineModel('data', { required: true })

// TODO: https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: Record<string, unknown> = {
  integer: CmkFormInteger,
  dictionary: CmkFormDictionary,
  string: CmkFormString
  //  legacy_valuespec: CmkFormLegacyValueSpec
}

// TODO: we should enforce an interface as return value?!
function get_component(): unknown {
  return components[props.spec.vue_type!]
}
</script>

<template>
  <component :is="get_component()" :spec="spec" :validation="validation" v-model:data="data">
  </component>
</template>
