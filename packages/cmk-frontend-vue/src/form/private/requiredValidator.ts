/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { staticAssertNever } from '@/lib/typeUtils'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

type RendersRequiredLabels =
  | FormSpec.Password
  | FormSpec.ConditionChoices
  | FormSpec.CascadingSingleChoice
  | FormSpec.SingleChoice
  | FormSpec.SingleChoiceEditable

function isTypeRenderingRequiredLabel(
  parameterForm: FormSpec.FormSpec
): parameterForm is RendersRequiredLabels {
  const type = parameterForm.type as RendersRequiredLabels['type']
  switch (type) {
    case 'password':
    case 'condition_choices':
    case 'cascading_single_choice':
    case 'single_choice':
    case 'single_choice_editable':
      return true
    default:
      staticAssertNever(type)
      return false
  }
}

export function rendersRequiredLabelItself(parameterForm: FormSpec.FormSpec): boolean {
  return (
    ('label' in parameterForm && !!parameterForm.label) ||
    isTypeRenderingRequiredLabel(parameterForm)
  )
}

export function required(validator: FormSpec.Validator): boolean {
  return (
    (validator.type === 'length_in_range' &&
      validator.min_value !== null &&
      validator.min_value > 0) ||
    (validator.type === 'number_in_range' &&
      validator.min_value !== null &&
      validator.min_value > 0)
  )
}
