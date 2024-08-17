<script setup lang="ts">
import FormInteger from '@/components/cmk-form/forms/FormInteger.vue'
import FormFloat from '@/components/cmk-form/forms/FormFloat.vue'
import FormString from '@/components/cmk-form/forms/FormString.vue'
import FormSingleChoice from '@/components/cmk-form/forms/FormSingleChoice.vue'
import FormDictionary from '@/components/cmk-form/forms/FormDictionary.vue'
import type { FormSpec, Components } from '@/vue_formspec_components'
import FormCascadingSingleChoice from '@/components/cmk-form/forms/FormCascadingSingleChoice.vue'
import FormList from '@/components/cmk-form/forms/FormList.vue'
import FormLegacyValueSpec from '@/components/cmk-form/forms/FormLegacyValueSpec.vue'
import type { IComponent } from '@/types'
import type { ValidationMessages } from '@/lib/validation'
import FormFixedValue from '@/components/cmk-form/forms/FormFixedValue.vue'
import FormBooleanChoice from '@/components/cmk-form/forms/FormBooleanChoice.vue'
import FormMultilineText from '@/components/cmk-form/forms/FormMultilineText.vue'
import FormHelp from '@/components/cmk-form/FormHelp.vue'
import FormDataSize from '@/components/cmk-form/forms/FormDataSize.vue'
import FormCatalog from '@/components/cmk-form/forms/FormCatalog.vue'

const props = defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })

// TODO: https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: Record<Components['type'], unknown> = {
  integer: FormInteger,
  dictionary: FormDictionary,
  string: FormString,
  float: FormFloat,
  single_choice: FormSingleChoice,
  cascading_single_choice: FormCascadingSingleChoice,
  list: FormList,
  legacy_valuespec: FormLegacyValueSpec,
  fixed_value: FormFixedValue,
  boolean_choice: FormBooleanChoice,
  multiline_text: FormMultilineText,
  data_size: FormDataSize,
  catalog: FormCatalog
}

function getComponent(): IComponent {
  const result = components[props.spec.type as Components['type']]
  if (result !== undefined) {
    return result as IComponent
  }
  throw new Error(`Could not find Component for type=${props.spec.type}`)
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
