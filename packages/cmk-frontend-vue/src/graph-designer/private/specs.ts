/**
 * Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

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

export function makeString(
  title: string,
  inputHint: string,
  autocompleter: null | FormSpec.Autocompleter,
  fieldSize: FormSpec.StringFieldSize = 'MEDIUM'
): FormSpec.String {
  return {
    type: 'string',
    title: title,
    help: '',
    label: null,
    validators: [],
    input_hint: inputHint,
    field_size: fieldSize,
    autocompleter: autocompleter
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
): FormSpec.TwoColumnDictionary {
  return {
    type: 'two_column_dictionary',
    title: title,
    help: '',
    validators: [],
    elements: elements,
    groups: [],
    no_elements_text: '',
    additional_static_elements: null
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
    no_elements_text: '',
    label: null,
    input_hint: '',
    layout: 'vertical'
  }
}
