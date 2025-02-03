/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable */
/**
 * This file is auto-generated via the cmk-shared-typing package.
 * Do not edit manually.
 */

export type Components =
  | Integer
  | Float
  | String
  | Dictionary
  | List
  | ListUniqueSelection
  | LegacyValuespec
  | SingleChoice
  | CascadingSingleChoice
  | FixedValue
  | BooleanChoice
  | MultilineText
  | CommentTextArea
  | Password
  | DataSize
  | Catalog
  | DualListChoice
  | CheckboxListChoice
  | TimeSpan
  | Metric
  | SingleChoiceEditable
  | Tuple
  | OptionalChoice
  | SimplePassword
  | ListOfStrings
  | Folder
  | ConditionChoices
  | Labels
  | FileUpload
  | TimeSpecific;
export type Integer = FormSpec & {
  type: "integer";
  label: string | null;
  unit: string | null;
  input_hint: string | null;
  i18n_base: I18NFormSpecBase;
};
export type Validator = IsInteger | IsFloat | NumberInRange | LengthInRange | MatchRegex;
export type Float = FormSpec & {
  type: "float";
  label: string | null;
  unit: string | null;
  input_hint: string | null;
  i18n_base: I18NFormSpecBase;
};
export type String = (FormSpec & {
  label: string | null;
  input_hint: string | null;
  field_size: StringFieldSize;
  autocompleter: null | Autocompleter;
  i18n_base: I18NFormSpecBase;
}) & {
  type: "string";
};
export type StringFieldSize = "SMALL" | "MEDIUM" | "LARGE";
export type Dictionary = FormSpec & {
  type: "dictionary";
  elements: DictionaryElement[];
  groups: DictionaryGroup[];
  no_elements_text: string;
  additional_static_elements: {} | null;
  layout: DictionaryLayout;
  i18n_base: I18NFormSpecBase;
};
export type DictionaryGroupLayout = "horizontal" | "vertical";
export type DictionaryLayout = "one_column" | "two_columns";
export type List = FormSpec & {
  type: "list";
  element_template: FormSpec;
  element_default_value: unknown;
  editable_order: boolean;
  add_element_label: string;
  remove_element_label: string;
  no_element_label: string;
};
export type ListUniqueSelection = FormSpec & {
  type: "list_unique_selection";
  element_template: SingleChoice | CascadingSingleChoice;
  element_default_value: unknown;
  add_element_label: string;
  remove_element_label: string;
  no_element_label: string;
  unique_selection_elements: string[];
};
export type SingleChoice = FormSpec & {
  type: "single_choice";
  elements: SingleChoiceElement[];
  no_elements_text: string | null;
  frozen: boolean;
  label: string | null;
  input_hint: string | null;
  i18n_base: I18NFormSpecBase;
};
export type CascadingSingleChoice = FormSpec & {
  type: "cascading_single_choice";
  elements: CascadingSingleChoiceElement[];
  label: string | null;
  input_hint: string | null;
  layout: CascadingSingleChoiceLayout;
  i18n_base: I18NFormSpecBase;
};
export type CascadingSingleChoiceLayout = "vertical" | "horizontal" | "button_group";
export type LegacyValuespec = FormSpec & {
  type: "legacy_valuespec";
  varprefix: string;
};
export type FixedValue = FormSpec & {
  type: "fixed_value";
  label: string | null;
  value: unknown;
};
export type BooleanChoice = FormSpec & {
  type: "boolean_choice";
  label: string | null;
  text_on: string;
  text_off: string;
};
export type MultilineText = (FormSpec & {
  label: string | null;
  macro_support: boolean;
  monospaced: boolean;
  input_hint: string | null;
}) & {
  type: "multiline_text";
};
export type CommentTextArea = ((FormSpec & {
  label: string | null;
  macro_support: boolean;
  monospaced: boolean;
  input_hint: string | null;
}) & {
  user_name: string;
  i18n: CommentTextAreaI18N;
}) & {
  type: "comment_text_area";
};
export type Password = FormSpec & {
  type: "password";
  password_store_choices: {
    password_id: string;
    name: string;
  }[];
  i18n: I18NPassword;
  i18n_base: I18NFormSpecBase;
};
export type DataSize = FormSpec & {
  type: "data_size";
  label: string | null;
  displayed_magnitudes: string[];
  input_hint: string | null;
  i18n: DataSizeI18N;
};
export type Catalog = FormSpec & {
  type: "catalog";
  elements: Topic[];
  i18n_base: I18NFormSpecBase;
};
export type DualListChoice = (FormSpec & {
  elements: MultipleChoiceElement[];
  show_toggle_all: boolean;
  autocompleter?: Autocompleter;
  i18n: DualListChoiceI18N;
}) & {
  type: "dual_list_choice";
};
export type CheckboxListChoice = FormSpec & {
  type: "checkbox_list_choice";
  elements: MultipleChoiceElement[];
  i18n: DualListChoiceI18N;
};
export type TimeSpan = FormSpec & {
  type: "time_span";
  label: string | null;
  i18n: TimeSpanI18N;
  displayed_magnitudes: TimeSpanTimeMagnitude[];
  input_hint: number | null;
};
export type TimeSpanTimeMagnitude = "millisecond" | "second" | "minute" | "hour" | "day";
export type Metric = ((FormSpec & {
  label: string | null;
  input_hint: string | null;
  field_size: StringFieldSize;
  autocompleter: null | Autocompleter;
  i18n_base: I18NFormSpecBase;
}) & {
  service_filter_autocompleter: Autocompleter;
  host_filter_autocompleter: Autocompleter;
  i18n: MetricI18N;
}) & {
  type: "metric";
};
export type SingleChoiceEditable = FormSpec & {
  type: "single_choice_editable";
  config_entity_type: string;
  config_entity_type_specifier: string;
  elements: SingleChoiceElement[];
  i18n: SingleChoiceEditableI18N;
  i18n_base: I18NFormSpecBase;
};
export type Tuple = FormSpec & {
  type: "tuple";
  elements: FormSpec[];
  layout: TupleLayout;
  show_titles: boolean;
};
export type TupleLayout = "horizontal_titles_top" | "horizontal" | "vertical" | "float";
export type OptionalChoice = FormSpec & {
  type: "optional_choice";
  parameter_form: FormSpec;
  i18n: I18NOptionalChoice;
  parameter_form_default_value: unknown;
};
export type SimplePassword = FormSpec & {
  type: "simple_password";
};
export type ListOfStrings = FormSpec & {
  type: "list_of_strings";
  string_spec: FormSpec;
  string_default_value: string;
  layout: ListOfStringsLayout;
};
export type ListOfStringsLayout = "horizontal" | "vertical";
export type Folder = FormSpec & {
  type: "folder";
  input_hint?: string;
};
export type ConditionChoices = FormSpec & {
  type: "condition_choices";
  condition_groups: {
    [k: string]: ConditionGroup;
  };
  i18n: ConditionChoicesI18N;
  i18n_base: I18NFormSpecBase;
};
export type Labels = FormSpec & {
  type: "labels";
  i18n: LabelsI18N;
  autocompleter: Autocompleter;
  max_labels: number | null;
  label_source: ("explicit" | "ruleset" | "discovered") | null;
};
export type FileUpload = FormSpec & {
  type: "file_upload";
  i18n: FileUploadI18N;
};
export type TimeSpecific = FormSpec & {
  type: "time_specific";
  time_specific_values_key: "tp_values";
  default_value_key: "tp_default_value";
  i18n: TimeSpecificI18N;
  parameter_form_enabled: FormSpec;
  parameter_form_disabled: FormSpec;
};
export type Values = ConditionChoicesValue;

export interface VueFormspecComponents {
  components?: Components;
  validation_message?: ValidationMessage;
  values?: Values;
}
export interface FormSpec {
  type: string;
  title: string;
  help: string;
  validators: Validator[];
}
export interface IsInteger {
  type: "is_integer";
  error_message: string;
}
export interface IsFloat {
  type: "is_float";
  error_message: string;
}
export interface NumberInRange {
  type: "number_in_range";
  min_value: number | null;
  max_value: number | null;
  error_message: string;
}
export interface LengthInRange {
  type: "length_in_range";
  min_value: number | null;
  max_value: number | null;
  error_message: string;
}
export interface MatchRegex {
  type: "match_regex";
  regex?: string;
  error_message?: string;
}
export interface I18NFormSpecBase {
  required: string;
}
export interface Autocompleter {
  fetch_method: "ajax_vs_autocomplete";
  data: AutocompleterData;
}
export interface AutocompleterData {
  ident: string;
  params: AutocompleterParams;
}
export interface AutocompleterParams {
  show_independent_of_context?: boolean;
  strict?: boolean;
  escape_regex?: boolean;
  world?: string;
  context?: {};
}
export interface DictionaryElement {
  name: string;
  required: boolean;
  group: DictionaryGroup | null;
  default_value: unknown;
  render_only: boolean;
  parameter_form: FormSpec;
}
export interface DictionaryGroup {
  key: string | null;
  title: string | null;
  help: string | null;
  layout: DictionaryGroupLayout;
}
export interface SingleChoiceElement {
  name: string;
  title: string;
}
export interface CascadingSingleChoiceElement {
  name: string;
  title: string;
  default_value: unknown;
  parameter_form: FormSpec;
}
export interface CommentTextAreaI18N {
  prefix_date_and_comment: string;
}
export interface I18NPassword {
  explicit_password: string;
  password_store: string;
  no_password_store_choices: string;
  password_choice_invalid: string;
  choose_password_from_store: string;
  choose_password_type: string;
}
export interface DataSizeI18N {
  choose_unit: string;
}
export interface Topic {
  name: string;
  title: string;
  elements: TopicGroup[] | TopicElement[];
}
export interface TopicGroup {
  type: "topic_group";
  title: string;
  elements: TopicElement[];
}
export interface TopicElement {
  type: "topic_element";
  name: string;
  required: boolean;
  parameter_form: FormSpec;
  default_value: unknown;
}
export interface MultipleChoiceElement {
  name: string;
  title: string;
}
export interface DualListChoiceI18N {
  add: string;
  remove: string;
  add_all: string;
  remove_all: string;
  available_options: string;
  selected_options: string;
  selected: string;
  no_elements_available: string;
  no_elements_selected: string;
  autocompleter_loading: string;
  search_available_options: string;
  search_selected_options: string;
  and_x_more: string;
}
export interface TimeSpanI18N {
  millisecond: string;
  second: string;
  minute: string;
  hour: string;
  day: string;
  validation_negative_number: string;
}
export interface MetricI18N {
  host_input_hint: string;
  host_filter: string;
  service_input_hint: string;
  service_filter: string;
}
export interface SingleChoiceEditableI18N {
  slidein_save_button: string;
  slidein_cancel_button: string;
  slidein_create_button: string;
  slidein_new_title: string;
  slidein_edit_title: string;
  edit: string;
  create: string;
  loading: string;
  no_objects: string;
  no_selection: string;
  validation_error: string;
  fatal_error: string;
  fatal_error_reload: string;
}
export interface I18NOptionalChoice {
  label: string;
  none_label: string;
}
export interface ConditionGroup {
  title: string;
  conditions: Condition[];
}
export interface Condition {
  name: string;
  title: string;
}
export interface ConditionChoicesI18N {
  choose_operator: string;
  choose_condition: string;
  add_condition_label: string;
  select_condition_group_to_add: string;
  no_more_condition_groups_to_add: string;
  eq_operator: string;
  ne_operator: string;
  or_operator: string;
  nor_operator: string;
}
export interface LabelsI18N {
  add_some_labels: string;
  remove_label: string;
  key_value_format_error: string;
  uniqueness_error: string;
  max_labels_reached: string;
}
export interface FileUploadI18N {
  replace_file: string;
}
export interface TimeSpecificI18N {
  enable: string;
  disable: string;
}
export interface ValidationMessage {
  location: string[];
  message: string;
  invalid_value: unknown;
}
export interface ConditionChoicesValue {
  group_name: string;
  value: Eq | Ne | Or | Nor;
}
export interface Eq {
  oper_eq: string;
}
export interface Ne {
  oper_ne: string;
}
export interface Or {
  oper_or: string[];
}
export interface Nor {
  oper_nor: string[];
}
