/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Components } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type Component } from 'vue'

import FormBinaryConditionChoices from '@/form/private/forms/FormBinaryConditionChoices'
import FormBooleanChoice from '@/form/private/forms/FormBooleanChoice.vue'
import FormCascadingSingleChoice from '@/form/private/forms/FormCascadingSingleChoice.vue'
import FormCatalog from '@/form/private/forms/FormCatalog/FormCatalog.vue'
import FormCheckboxListChoice from '@/form/private/forms/FormCheckboxListChoice.vue'
import FormCommentTextArea from '@/form/private/forms/FormCommentTextArea.vue'
import FormConditionChoices from '@/form/private/forms/FormConditionChoices'
import FormDataSize from '@/form/private/forms/FormDataSize.vue'
import FormDatePicker from '@/form/private/forms/FormDatePicker.vue'
import FormDictionary from '@/form/private/forms/FormDictionary/FormDictionary.vue'
import FormTwoColumnDictionary from '@/form/private/forms/FormDictionary/FormTwoColumnDictionary.vue'
import FormDualListChoice from '@/form/private/forms/FormDualListChoice.vue'
import FormFileUpload from '@/form/private/forms/FormFileUpload.vue'
import FormFixedValue from '@/form/private/forms/FormFixedValue.vue'
import FormFloat from '@/form/private/forms/FormFloat.vue'
import FormInteger from '@/form/private/forms/FormInteger.vue'
import FormLabels from '@/form/private/forms/FormLabels.vue'
import FormLegacyValueSpec from '@/form/private/forms/FormLegacyValueSpec.vue'
import FormList from '@/form/private/forms/FormList/FormList.vue'
import FormListUniqueSelection from '@/form/private/forms/FormList/FormListUniqueSelection.vue'
import FormListOfStrings from '@/form/private/forms/FormListOfStrings.vue'
import FormMetric from '@/form/private/forms/FormMetric.vue'
import FormMetricBackendCustomQuery from '@/form/private/forms/FormMetricBackendCustomQuery.vue'
import FormMultilineText from '@/form/private/forms/FormMultilineText.vue'
import FormOAuth2ConnectionSetup from '@/form/private/forms/FormOAuth2ConnectionSetup.vue'
import FormOptionalChoice from '@/form/private/forms/FormOptionalChoice.vue'
import FormPassword from '@/form/private/forms/FormPassword.vue'
import FormRegex from '@/form/private/forms/FormRegex/FormRegex.vue'
import FormSimplePassword from '@/form/private/forms/FormSimplePassword.vue'
import FormSingleChoice from '@/form/private/forms/FormSingleChoice.vue'
import FormSingleChoiceEditable from '@/form/private/forms/FormSingleChoiceEditable/FormSingleChoiceEditable.vue'
import FormString from '@/form/private/forms/FormString.vue'
import FormTimePicker from '@/form/private/forms/FormTimePicker.vue'
import FormTimeSpan from '@/form/private/forms/FormTimeSpan/FormTimeSpan.vue'
import FormTimeSpecific from '@/form/private/forms/FormTimeSpecific.vue'
import FormTuple from '@/form/private/forms/FormTuple.vue'

// TODO: https://forum.vuejs.org/t/use-typescript-to-make-sure-a-vue3-component-has-certain-props/127239/9
const components: Record<Components['type'], Component> = {
  binary_condition_choices: FormBinaryConditionChoices,
  boolean_choice: FormBooleanChoice,
  cascading_single_choice: FormCascadingSingleChoice,
  catalog: FormCatalog,
  checkbox_list_choice: FormCheckboxListChoice,
  comment_text_area: FormCommentTextArea,
  condition_choices: FormConditionChoices,
  data_size: FormDataSize,
  date_picker: FormDatePicker,
  time_picker: FormTimePicker,
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
  metric_backend_custom_query: FormMetricBackendCustomQuery,
  oauth2_connection_setup: FormOAuth2ConnectionSetup,
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
  tuple: FormTuple,
  regex: FormRegex
}

export function getComponent(type: string): Component {
  const result = components[type as Components['type']]
  if (result !== undefined) {
    return result
  }
  throw new Error(`Could not find Component for type=${type}`)
}
