<script setup lang="ts">
import CmkFormInteger from './element/CmkFormInteger.vue'
import CmkFormFloat from '@/components/cmk-form/element/CmkFormFloat.vue'
import CmkFormString from './element/CmkFormString.vue'
import CmkFormSingleChoice from './element/CmkFormSingleChoice.vue'
import CmkFormDictionary from './container/CmkFormDictionary.vue'
import type { ValidationMessages } from '@/utils'
import type { VueSchema } from '@/vue_formspec_components'
import CmkFormCascadingSingleChoice from '@/components/cmk-form/container/CmkFormCascadingSingleChoice.vue'
import CmkFormList from '@/components/cmk-form/container/CmkFormList.vue'
import CmkFormLegacyValueSpec from '@/components/cmk-form/element/CmkFormLegacyValueSpec.vue'

const props = defineProps<{
  spec: VueSchema
  validation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })

// TODO: https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: Record<string, unknown> = {
  integer: CmkFormInteger,
  dictionary: CmkFormDictionary,
  string: CmkFormString,
  float: CmkFormFloat,
  single_choice: CmkFormSingleChoice,
  cascading_single_choice: CmkFormCascadingSingleChoice,
  list: CmkFormList,
  legacy_valuespec: CmkFormLegacyValueSpec
}

// TODO: we should enforce an interface as return value?!
function get_component(): unknown {
  return components[props.spec.vue_type!]
}
</script>

<template>
  <component :is="get_component()" v-model:data="data" :spec="spec" :validation="validation">
  </component>
</template>
