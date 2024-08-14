<script setup lang="ts">
import FormInteger from '@/form/components/forms/FormInteger.vue'
import FormFloat from '@/form/components/forms/FormFloat.vue'
import FormString from '@/form/components/forms/FormString.vue'
import FormSingleChoice from '@/form/components/forms/FormSingleChoice.vue'
import FormDictionary from '@/form/components/forms/FormDictionary.vue'
import type { FormSpec, Components } from '@/form/components/vue_formspec_components'
import FormCascadingSingleChoice from '@/form/components/forms/FormCascadingSingleChoice.vue'
import FormList from '@/form/components/forms/FormList.vue'
import FormLegacyValueSpec from '@/form/components/forms/FormLegacyValueSpec.vue'
import type { IComponent } from '@/types'
import FormFixedValue from '@/form/components/forms/FormFixedValue.vue'
import FormBooleanChoice from '@/form/components/forms/FormBooleanChoice.vue'
import FormMultilineText from '@/form/components/forms/FormMultilineText.vue'
import FormHelp from '@/form/components/FormHelp.vue'
import FormDataSize from '@/form/components/forms/FormDataSize.vue'
import FormCatalog from '@/form/components/forms/FormCatalog.vue'
import FormTimeSpan from '@/form/components/forms/FormTimeSpan.vue'
import type { ValidationMessages } from '@/form/components/utils/validation'
import FormMultipleChoice from '@/form/components/forms/FormMultipleChoice.vue'
import FormPassword from './forms/FormPassword.vue'

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
  time_span: FormTimeSpan,
  boolean_choice: FormBooleanChoice,
  multiline_text: FormMultilineText,
  multiple_choice: FormMultipleChoice,
  password: FormPassword,
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
