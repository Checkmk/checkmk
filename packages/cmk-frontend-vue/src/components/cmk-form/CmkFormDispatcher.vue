<script setup lang="ts">
import CmkFormInteger from './element/CmkFormInteger.vue'
import CmkFormFloat from '@/components/cmk-form/element/CmkFormFloat.vue'
import CmkFormString from './element/CmkFormString.vue'
import CmkFormSingleChoice from './element/CmkFormSingleChoice.vue'
import CmkFormDictionary from './container/CmkFormDictionary.vue'
import type { FormSpec, Components } from '@/vue_formspec_components'
import CmkFormCascadingSingleChoice from '@/components/cmk-form/container/CmkFormCascadingSingleChoice.vue'
import CmkFormList from '@/components/cmk-form/container/CmkFormList.vue'
import CmkFormLegacyValueSpec from '@/components/cmk-form/element/CmkFormLegacyValueSpec.vue'
import type { IComponent } from '@/types'
import type { ValidationMessages } from '@/lib/validation'
import CmkFormFixedValue from '@/components/cmk-form/element/CmkFormFixedValue.vue'
import CmkFormBooleanChoice from '@/components/cmk-form/element/CmkFormBooleanChoice.vue'
import CmkFormMultilineText from '@/components/cmk-form/element/CmkFormMultilineText.vue'
import FormHelp from '@/components/cmk-form/FormHelp.vue'
import CmkFormDataSize from '@/components/cmk-form/element/CmkFormDataSize.vue'
import CmkFormCatalog from '@/components/cmk-form/element/CmkFormCatalog.vue'

const props = defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })

// TODO: https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: Record<Components['type'], unknown> = {
  integer: CmkFormInteger,
  dictionary: CmkFormDictionary,
  string: CmkFormString,
  float: CmkFormFloat,
  single_choice: CmkFormSingleChoice,
  cascading_single_choice: CmkFormCascadingSingleChoice,
  list: CmkFormList,
  legacy_valuespec: CmkFormLegacyValueSpec,
  fixed_value: CmkFormFixedValue,
  boolean_choice: CmkFormBooleanChoice,
  multiline_text: CmkFormMultilineText,
  data_size: CmkFormDataSize,
  catalog: CmkFormCatalog
}

function getComponent(): IComponent {
  return components[props.spec.type as Components['type']] as IComponent
}
</script>

<template>
  <div>
    <FormHelp :help="spec.help" />
    <component
      :is="getComponent()"
      v-model:data="data"
      :backend-validation="backendValidation"
      :spec="spec"
    />
  </div>
</template>
