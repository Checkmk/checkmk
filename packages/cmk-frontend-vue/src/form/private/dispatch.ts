/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { type Component } from 'vue'
import type { Components } from 'cmk-shared-typing/typescript/vue_formspec_components'

import FormBooleanChoice from '@/form/components/forms/FormBooleanChoice.vue'
import FormCascadingSingleChoice from '@/form/components/forms/FormCascadingSingleChoice.vue'
import FormCatalog from '@/form/components/forms/form_catalog/FormCatalog.vue'
import FormConditionChoices from '@/form/components/forms/FormConditionChoices'
import FormCheckboxListChoice from '@/form/components/forms/FormCheckboxListChoice.vue'
import FormCommentTextArea from '@/form/components/forms/FormCommentTextArea.vue'
import FormMetric from '../components/forms/FormMetric.vue'
import FormDataSize from '@/form/components/forms/FormDataSize.vue'
import FormDictionary from '@/form/components/forms/FormDictionary/FormDictionary.vue'
import FormDualListChoice from '@/form/components/forms/FormDualListChoice.vue'
import FormFixedValue from '@/form/components/forms/FormFixedValue.vue'
import FormFloat from '@/form/components/forms/FormFloat.vue'
import FormInteger from '@/form/components/forms/FormInteger.vue'
import FormLabels from '@/form/components/forms/FormLabels.vue'
import FormLegacyValueSpec from '@/form/components/forms/FormLegacyValueSpec.vue'
import FormList from '@/form/components/forms/FormList.vue'
import FormListUniqueSelection from '@/form/components/forms/FormListUniqueSelection.vue'
import FormListOfStrings from '@/form/components/forms/FormListOfStrings.vue'
import FormMultilineText from '@/form/components/forms/FormMultilineText.vue'
import FormOptionalChoice from '@/form/components/forms/FormOptionalChoice.vue'
import FormPassword from '@/form/components/forms/FormPassword.vue'
import FormSimplePassword from '@/form/components/forms/FormSimplePassword.vue'
import FormSingleChoiceEditable from '@/form/components/forms/FormSingleChoiceEditable.vue'
import FormSingleChoice from '@/form/components/forms/FormSingleChoice.vue'
import FormString from '@/form/components/forms/FormString.vue'
import FormTimeSpan from '@/form/components/forms/FormTimeSpan.vue'
import FormTuple from '@/form/components/forms/FormTuple.vue'
import FormTimeSpecific from '@/form/components/forms/FormTimeSpecific.vue'
import FormFileUpload from '@/form/components/forms/FormFileUpload.vue'
import FormTwoColumnDictionary from '../components/forms/FormDictionary/FormTwoColumnDictionary.vue'

// TODO: https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: Record<Components['type'], Component> = {
  boolean_choice: FormBooleanChoice,
  cascading_single_choice: FormCascadingSingleChoice,
  catalog: FormCatalog,
  checkbox_list_choice: FormCheckboxListChoice,
  comment_text_area: FormCommentTextArea,
  condition_choices: FormConditionChoices,
  data_size: FormDataSize,
  dictionary: FormDictionary,
  two_column_dictionary: FormTwoColumnDictionary,
  dual_list_choice: FormDualListChoice,
  file_upload: FormFileUpload,
  fixed_value: FormFixedValue,
  float: FormFloat,
  integer: FormInteger,
  labels: FormLabels,
  legacy_valuespec: FormLegacyValueSpec,
  list: FormList,
  list_unique_selection: FormListUniqueSelection,
  list_of_strings: FormListOfStrings,
  metric: FormMetric,
  multiline_text: FormMultilineText,
  optional_choice: FormOptionalChoice,
  password: FormPassword,
  simple_password: FormSimplePassword,
  single_choice_editable: FormSingleChoiceEditable,
  single_choice: FormSingleChoice,
  string: FormString,
  time_span: FormTimeSpan,
  time_specific: FormTimeSpecific,
  tuple: FormTuple
}

export function getComponent(type: string): Component {
  const result = components[type as Components['type']]
  if (result !== undefined) {
    return result
  }
  throw new Error(`Could not find Component for type=${type}`)
}
