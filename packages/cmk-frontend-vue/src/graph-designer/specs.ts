/**
 * Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type * as FormSpec from '@/form/components/vue_formspec_components'

export function makeFloat(title: string, label: string): FormSpec.Float {
  return {
    type: 'float',
    title: title,
    help: '',
    validators: [],
    unit: null,
    label: label,
    input_hint: null
  }
}

export function makeString(title: string): FormSpec.String {
  return {
    type: 'string',
    title: title,
    help: '',
    validators: [],
    input_hint: 'symbol',
    field_size: 'SMALL',
    autocompleter: null
  }
}

export function makeFixedValue(): FormSpec.FixedValue {
  return {
    type: 'fixed_value',
    title: '',
    help: '',
    validators: [],
    label: null,
    value: null
  }
}

export function makeBooleanChoice(): FormSpec.BooleanChoice {
  return {
    type: 'boolean_choice',
    title: '',
    help: '',
    validators: [],
    label: null,
    text_on: '',
    text_off: ''
  }
}

export function makeSingleChoice(
  title: string,
  elements: FormSpec.SingleChoiceElement[]
): FormSpec.SingleChoice {
  return {
    type: 'single_choice',
    title: title,
    help: '',
    validators: [],
    elements: elements,
    no_elements_text: '',
    frozen: false,
    label: null,
    input_hint: null
  }
}

export function makeDictionary(
  title: string,
  elements: FormSpec.DictionaryElement[]
): FormSpec.Dictionary {
  return {
    type: 'dictionary',
    title: title,
    help: '',
    validators: [],
    elements: elements,
    groups: [],
    no_elements_text: '',
    additional_static_elements: null,
    layout: 'two_columns'
  }
}

export function makeCascadingSingleChoice(
  title: string,
  elements: FormSpec.CascadingSingleChoiceElement[]
): FormSpec.CascadingSingleChoice {
  return {
    type: 'cascading_single_choice',
    title: title,
    help: '',
    validators: [],
    elements: elements,
    label: null,
    input_hint: '',
    layout: 'vertical'
  }
}
