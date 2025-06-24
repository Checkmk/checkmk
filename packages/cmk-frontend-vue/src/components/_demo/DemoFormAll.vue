<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkCheckbox from '@/components/CmkCheckbox.vue'
import FormEdit from '@/form/components/FormEdit.vue'
import type {
  BooleanChoice,
  CascadingSingleChoice,
  CheckboxListChoice,
  CommentTextArea,
  Components,
  ConditionChoices,
  DataSize,
  Dictionary,
  DualListChoice,
  FileUpload,
  FixedValue,
  Float,
  FormSpec,
  Integer,
  Labels,
  List,
  ListOfStrings,
  ListUniqueSelection,
  MultilineText,
  OptionalChoice,
  Password,
  SimplePassword,
  SingleChoice,
  SingleChoiceEditable,
  String,
  TimeSpan,
  TimeSpecific,
  Tuple,
  TwoColumnDictionary
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

function getLabel(name: string) {
  if (showLabel.value) {
    return `${name} label`
  }
  return null
}
function getHelp(name: string) {
  if (showHelp.value) {
    return `${name} help`
  }
  return ''
}
function getTitle(name: string) {
  return `${name} title`
}
function getInputHint(name: string) {
  if (showInputHint.value) {
    return `${name} input hint`
  }
  return null
}
function getInputHintNumber(_name: string) {
  if (showInputHint.value) {
    return 9.99
  }
  return null
}

function getFormSpecDefaults(name: string): Omit<FormSpec, 'type'> {
  return {
    title: getTitle(name),
    help: getHelp(name),
    validators: []
  }
}

// long list of formspecs

function getInteger(name: string, options?: Partial<Omit<Integer, 'type'>>): Integer {
  return {
    type: 'integer',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    input_hint: '',
    unit: 'unit',
    i18n_base: { required: 'i18n required' },
    ...(options || {})
  }
}

function getFloat(name: string, options?: Partial<Omit<Float, 'type'>>): Float {
  return {
    type: 'float',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    input_hint: getInputHint(name),
    unit: 'unit',
    i18n_base: { required: 'i18n required' },
    ...options
  }
}

function getString(name: string, options?: Partial<Omit<String, 'type'>>): String {
  return {
    type: 'string',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    i18n_base: { required: 'i18n required' },
    input_hint: getInputHint(name),
    field_size: 'MEDIUM',
    autocompleter: null,
    ...options
  }
}

function getDictionary(name: string, options?: Partial<Omit<Dictionary, 'type'>>): Dictionary {
  return {
    type: 'dictionary',
    ...getFormSpecDefaults(name),
    elements: [
      {
        name: 'one_element',
        required: true,
        render_only: false,
        group: null,
        default_value: 'default value required',
        parameter_form: getString('required_string_in_dict')
      },
      {
        name: 'two_element',
        required: false,
        render_only: false,
        group: null,
        default_value: 'default value optional',
        parameter_form: getString('optional_string_in_dict')
      }
    ],
    groups: [],
    no_elements_text: 'i18n no elements text',
    additional_static_elements: null,
    i18n_base: { required: 'i18n required' },
    ...options
  }
}

function getDictionaryTwoColumns(
  name: string,
  options?: Partial<Omit<TwoColumnDictionary, 'type'>>
): TwoColumnDictionary {
  return {
    type: 'two_column_dictionary',
    ...getFormSpecDefaults(name),
    elements: [
      {
        name: 'one_element',
        required: true,
        render_only: false,
        group: null,
        default_value: 'default value required',
        parameter_form: getString('required_string_in_dict')
      },
      {
        name: 'two_element',
        required: false,
        render_only: false,
        group: null,
        default_value: 'default value optional',
        parameter_form: getString('optional_string_in_dict')
      }
    ],
    groups: [],
    no_elements_text: 'i18n no elements text',
    additional_static_elements: null,
    i18n_base: { required: 'i18n required' },
    ...options
  }
}

function getList(name: string, options?: Partial<Omit<List, 'type'>>): List {
  return {
    type: 'list',
    ...getFormSpecDefaults(name),
    element_template: getString('some_string_in_list'),
    element_default_value: 'default value',
    editable_order: true,
    add_element_label: 'i18n add element',
    remove_element_label: 'i18n remove element',
    no_element_label: 'i18n no element',
    ...options
  }
}

function getListUniqueSelection(
  name: string,
  options?: Partial<Omit<ListUniqueSelection, 'type'>>
): ListUniqueSelection {
  return {
    type: 'list_unique_selection',
    ...getFormSpecDefaults(name),
    element_template: getSingleChoice('some_single_choice_in_unique_selection'),
    element_default_value: 'one',
    add_element_label: 'i18n add element',
    remove_element_label: 'i18n remove element',
    no_element_label: 'i18n no element',
    unique_selection_elements: ['one', 'two'],
    ...options
  }
}

function getSingleChoice(
  name: string,
  options?: Partial<Omit<SingleChoice, 'type'>>
): SingleChoice {
  return {
    type: 'single_choice',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    elements: [
      { name: 'one', title: 'one title' },
      { name: 'two', title: 'two title' },
      { name: 'three', title: 'three title' }
    ],
    no_elements_text: 'i18n no elements text',
    frozen: false,
    input_hint: getInputHint(name),
    i18n_base: { required: 'i18n required' },
    ...options
  }
}

function getCascadingSingleChoice(
  name: string,
  options?: Partial<Omit<CascadingSingleChoice, 'type'>>
): CascadingSingleChoice {
  return {
    type: 'cascading_single_choice',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    input_hint: getInputHint(name),
    no_elements_text: '',
    elements: [
      {
        name: 'name one',
        title: 'title one',
        default_value: 'default value',
        parameter_form: getString('some_string_in_cascading_single_choice')
      },
      {
        name: 'name two',
        title: 'title two',
        default_value: -1,
        parameter_form: getInteger('some_integer_in_cascading_single_choice')
      }
    ],
    layout: 'vertical',
    i18n_base: { required: 'i18n required' },
    ...options
  }
}

function getFixedValue(name: string, options?: Partial<Omit<FixedValue, 'type'>>): FixedValue {
  return {
    type: 'fixed_value',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    value: `some_fixed_value_${name}`,
    ...options
  }
}

function getBooleanChoice(
  name: string,
  options?: Partial<Omit<BooleanChoice, 'type'>>
): BooleanChoice {
  return {
    type: 'boolean_choice',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    text_on: 'i18n text on',
    text_off: 'i18n text off',
    ...options
  }
}

function getMultilineText(
  name: string,
  options?: Partial<Omit<MultilineText, 'type'>>
): MultilineText {
  return {
    type: 'multiline_text',
    ...getFormSpecDefaults(name),
    input_hint: getInputHint(name),
    label: getLabel(name),
    macro_support: false,
    monospaced: true,
    ...options
  }
}

function getCommentTextArea(
  name: string,
  options?: Partial<Omit<CommentTextArea, 'type'>>
): CommentTextArea {
  return {
    type: 'comment_text_area',
    ...getFormSpecDefaults(name),
    input_hint: getInputHint(name),
    label: getLabel(name),
    macro_support: false,
    monospaced: true,
    user_name: 'user name',
    i18n: {
      prefix_date_and_comment: 'i18n prefix data and comment'
    },
    ...options
  }
}

function getPassword(name: string, options?: Partial<Omit<Password, 'type'>>): Password {
  return {
    type: 'password',
    ...getFormSpecDefaults(name),
    password_store_choices: [
      {
        password_id: 'one',
        name: 'name one'
      }
    ],
    i18n_base: { required: 'i18n required' },
    i18n: {
      choose_password_type: 'i18n choose_password_type',
      choose_password_from_store: 'i18n choose_password_from_store',
      explicit_password: 'i18n explicit_password',
      password_store: 'i18n password_store',
      no_password_store_choices: 'i18n no_password_store_choices',
      password_choice_invalid: 'i18n password_choice_invalid'
    },
    ...options
  }
}

function getDataSize(name: string, options?: Partial<Omit<DataSize, 'type'>>): DataSize {
  return {
    type: 'data_size',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    input_hint: getInputHint(name),
    displayed_magnitudes: ['one', 'two'],
    validators: [],
    i18n: {
      choose_unit: 'i18n choose_unit'
    },
    ...options
  }
}

function getDualListChoice(
  name: string,
  options?: Partial<Omit<DualListChoice, 'type'>>
): DualListChoice {
  return {
    type: 'dual_list_choice',
    ...getFormSpecDefaults(name),
    elements: [
      { name: 'one', title: 'title one' },
      { name: 'two', title: 'title two' }
    ],
    show_toggle_all: true,
    i18n: {
      add: 'i18n add',
      remove: 'i18n remove',
      add_all: 'i18n add_all',
      remove_all: 'i18n remove_all',
      available_options: 'i18n available_options',
      selected_options: 'i18n selected_options',
      selected: 'i18n selected',
      no_elements_available: 'i18n no_elements_available',
      no_elements_selected: 'i18n no_elements_selected',
      autocompleter_loading: 'i18n autocompleter_loading',
      search_selected_options: 'i18n search selected options',
      search_available_options: 'i18n search available options',
      and_x_more: 'i18n and_x_more'
    },
    ...options
  }
}

function getCheckboxListChoice(
  name: string,
  options?: Partial<Omit<CheckboxListChoice, 'type'>>
): CheckboxListChoice {
  return {
    type: 'checkbox_list_choice',
    ...getFormSpecDefaults(name),
    elements: [
      { name: 'one', title: 'title one' },
      { name: 'two', title: 'title two' }
    ],
    i18n: {
      add: 'i18n add',
      remove: 'i18n remove',
      add_all: 'i18n add_all',
      remove_all: 'i18n remove_all',
      available_options: 'i18n available_options',
      selected_options: 'i18n selected_options',
      selected: 'i18n selected',
      no_elements_available: 'i18n no_elements_available',
      no_elements_selected: 'i18n no_elements_selected',
      autocompleter_loading: 'i18n autocompleter_loading',
      search_selected_options: 'i18n search selected options',
      search_available_options: 'i18n search available options',
      and_x_more: 'i18n and_x_more'
    },
    ...options
  }
}

function getTimeSpan(name: string, options?: Partial<Omit<TimeSpan, 'type'>>): TimeSpan {
  return {
    type: 'time_span',
    ...getFormSpecDefaults(name),
    label: getLabel(name),
    displayed_magnitudes: ['second', 'minute', 'hour'],
    i18n: {
      validation_negative_number: 'i18n_validation_negative_number',
      millisecond: 'i18n millisecond',
      second: 'i18n second',
      minute: 'i18n minute',
      hour: 'i18n hour',
      day: 'i18n day'
    },
    input_hint: getInputHintNumber(name),
    ...options
  }
}

function getSingleChoiceEditable(
  name: string,
  options?: Partial<Omit<SingleChoiceEditable, 'type'>>
): SingleChoiceEditable {
  return {
    type: 'single_choice_editable',
    ...getFormSpecDefaults(name),
    config_entity_type: 'config_entity_type',
    config_entity_type_specifier: 'config_entity_type_specifier',
    elements: [{ name: 'one', title: 'one title' }],
    allow_editing_existing_elements: true,
    i18n_base: { required: 'i18n required' },
    i18n: {
      slidein_save_button: 'i18n slidein_save_button',
      slidein_cancel_button: 'i18n slidein_cancel_button',
      slidein_create_button: 'i18n slidein_create_button',
      slidein_new_title: 'i18n slidein_new_title',
      slidein_edit_title: 'i18n slidein_edit_title',
      edit: 'i18n edit',
      create: 'i18n create',
      loading: 'i18n loading',
      no_objects: 'i18n no_objects',
      no_selection: 'i18n no_selection',
      validation_error: 'i18n validation_error',
      fatal_error: 'i18n fatal_error',
      fatal_error_reload: 'i18n fatal_error_reload',
      permanent_change_warning: 'i18n permanent_change_warning',
      permanent_change_warning_dismiss: 'i18n permanent_change_warning_dismiss'
    },
    ...options
  }
}

function getTuple(name: string, options?: Partial<Omit<Tuple, 'type'>>): Tuple {
  return {
    type: 'tuple',
    ...getFormSpecDefaults(name),
    elements: [getString('one'), getString('two')],
    layout: 'horizontal',
    show_titles: true,
    ...options
  }
}

function getOptionalChoice(
  name: string,
  options?: Partial<Omit<OptionalChoice, 'type'>>
): OptionalChoice {
  return {
    type: 'optional_choice',
    ...getFormSpecDefaults(name),
    parameter_form: getString('string_in_optiona_choice'),
    parameter_form_default_value: 'default value',
    i18n: {
      label: 'i18n label',
      none_label: 'i18n none_label'
    },
    ...options
  }
}

function getSimplePassword(
  name: string,
  options?: Partial<Omit<SimplePassword, 'type'>>
): SimplePassword {
  return {
    type: 'simple_password',
    ...getFormSpecDefaults(name),
    ...options
  }
}

function getListOfStrings(
  name: string,
  options?: Partial<Omit<ListOfStrings, 'type'>>
): ListOfStrings {
  return {
    type: 'list_of_strings',
    ...getFormSpecDefaults(name),
    string_spec: getString('string in list of strings'),
    string_default_value: 'default_value',
    layout: 'horizontal',
    ...options
  }
}

function getConditionChoices(
  name: string,
  options?: Partial<Omit<ConditionChoices, 'type'>>
): ConditionChoices {
  return {
    type: 'condition_choices',
    ...getFormSpecDefaults(name),
    condition_groups: {
      group1: {
        title: 'Group 1',
        conditions: [
          { name: 'condition1', title: 'Condition 1' },
          { name: 'condition2', title: 'Condition 2' }
        ]
      }
    }, // TODO?
    i18n: {
      choose_operator: 'i18n choose_operator',
      choose_condition: 'i18n choose_condition',
      add_condition_label: 'i18n add_condition_label',
      select_condition_group_to_add: 'i18n select_condition_group_to_add',
      no_more_condition_groups_to_add: 'i18n no_more_condition_groups_to_add',
      eq_operator: 'i18n eq_operator',
      ne_operator: 'i18n ne_operator',
      or_operator: 'i18n or_operator',
      nor_operator: 'i18n nor_operator'
    },
    i18n_base: { required: 'required' },
    ...options
  }
}

function getLabels(name: string, options?: Partial<Omit<Labels, 'type'>>): Labels {
  return {
    type: 'labels',
    ...getFormSpecDefaults(name),
    autocompleter: {
      fetch_method: 'ajax_vs_autocomplete',
      data: {
        ident: 'label',
        params: {
          world: 'CONFIG'
        }
      }
    },
    max_labels: null,
    label_source: 'explicit',
    i18n: {
      remove_label: 'i18n remove_label',
      add_some_labels: 'i18n add_some_labels',
      key_value_format_error: 'i18n key_value_format_error',
      uniqueness_error: 'i18n uniqueness_error',
      max_labels_reached: 'i18n max_labels_reached'
    },
    ...options
  }
}

function getFileUpload(name: string, options?: Partial<Omit<FileUpload, 'type'>>): FileUpload {
  return {
    type: 'file_upload',
    ...getFormSpecDefaults(name),
    i18n: {
      replace_file: 'i18n replace_file'
    },
    ...options
  }
}

function getTimeSpecific(
  name: string,
  options?: Partial<Omit<TimeSpecific, 'type'>>
): TimeSpecific {
  return {
    type: 'time_specific',
    ...getFormSpecDefaults(name),
    time_specific_values_key: 'tp_values',
    default_value_key: 'tp_default_value',
    i18n: {
      enable: 'i18n enable',
      disable: 'i18n disable'
    },
    parameter_form_enabled: getString('in_time_specific_enable'),
    parameter_form_disabled: getString('in_time_specific_disable'),
    ...options
  }
}

const forms: Array<[string, (name: string) => Components, unknown]> = [
  ['BooleanChoice', getBooleanChoice, false],
  ['CascadingSingleChoice', getCascadingSingleChoice, ['one', undefined]],
  ['CheckboxListChoice', getCheckboxListChoice, []],
  ['CommentTextArea', getCommentTextArea, ''],
  [
    'ConditionChoices',
    getConditionChoices,
    [{ group_name: 'group1', value: { oper_eq: 'condition1' } }]
  ],
  ['DataSize', getDataSize, ['one', 'two']],
  ['Dictionary', getDictionary, {}],
  ['Dictionary--TwoColumns', getDictionaryTwoColumns, {}],
  ['DualListChoice', getDualListChoice, []],
  [
    'FileUpload',
    getFileUpload,
    { input_uuid: 'smth', file_name: null, file_type: null, file_content_encrypted: null }
  ],
  ['FixedValue', getFixedValue, undefined],
  ['Float', getFloat, 0],
  ['Integer', getInteger, 0],
  ['Labels', getLabels, { some: 'thing' }],
  ['List', getList, []],
  ['ListOfStrings', getListOfStrings, []],
  ['ListUniqueSelection', getListUniqueSelection, []],
  ['MultilineText', getMultilineText, ''],
  ['OptionalChoice', getOptionalChoice, 'one'],
  ['Password', getPassword, ['explicit_password', 'one', 'two', false]],
  ['SimplePassword', getSimplePassword, [['password', false]]],
  ['SingleChoiceEditable', getSingleChoiceEditable, 'one'],
  ['SingleChoice', getSingleChoice, 'one'],
  ['String', getString, ''],
  ['TimeSpan', getTimeSpan, null],
  ['TimeSpecific', getTimeSpecific, 'one'],
  ['Tuple', getTuple, ['one', 'two']]
]

const validation = computed(() => {
  if (showValidation.value) {
    return forms.map(([name, getter, defaultValue]) => {
      if (name === undefined || getter === undefined) {
        throw new Error()
      }
      return {
        location: [name],
        message: 'some validation problem',
        replacement_value: defaultValue
      }
    })
  } else {
    return []
  }
})

const showValidation = ref<boolean>(false)
const showHelp = ref<boolean>(true)
const showLabel = ref<boolean>(true)
const showInputHint = ref<boolean>(true)
const requiredDictionaryKeys = ref<boolean>(true)

const spec = computed(() => {
  return getDictionary('main', {
    elements: forms.map(([name, getter, defaultValue]) => {
      if (name === undefined || getter === undefined) {
        throw new Error()
      }
      return {
        name: name,
        required: requiredDictionaryKeys.value,
        group: null,
        render_only: false,
        default_value: defaultValue,
        parameter_form: getter(name)
      }
    })
  })
})

const data = ref<Record<string, string>>({})
</script>

<template>
  <div>
    <CmkCheckbox v-model="requiredDictionaryKeys" label="required dictionary keys" />
  </div>
  <div>
    <CmkCheckbox v-model="showValidation" label="show validation" />
  </div>
  <div>
    <CmkCheckbox v-model="showHelp" label="show help" />
  </div>
  <div>
    <CmkCheckbox v-model="showLabel" label="show label" />
  </div>
  <div>
    <CmkCheckbox v-model="showInputHint" label="show input hint" />
  </div>
  <hr />
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
