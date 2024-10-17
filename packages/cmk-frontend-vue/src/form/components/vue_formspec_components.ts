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
  | SingleChoiceEditable
  | Tuple
  | OptionalChoice
  | SimplePassword
  | ListOfStrings
  | Folder
  | Labels;
export type Integer = FormSpec & {
  type: "integer";
  label: string | null;
  unit: string | null;
  input_hint: string | null;
};
export type Validator = IsInteger | IsFloat | NumberInRange | LengthInRange | MatchRegex;
export type Float = FormSpec & {
  type: "float";
  label: string | null;
  unit: string | null;
  input_hint: string | null;
};
export type String = FormSpec & {
  type: "string";
  input_hint: string | null;
  field_size: StringFieldSize;
  autocompleter: null | Autocompleter;
};
export type StringFieldSize = "SMALL" | "MEDIUM" | "LARGE";
export type Dictionary = FormSpec & {
  type: "dictionary";
  elements: DictionaryElement[];
  groups: DictionaryGroup[];
  no_elements_text: string;
  additional_static_elements: {} | null;
  layout: DictionaryLayout;
};
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
export type LegacyValuespec = FormSpec & {
  type: "legacy_valuespec";
  input_html: string;
  readonly_html: string;
  varprefix: string;
};
export type SingleChoice = FormSpec & {
  type: "single_choice";
  elements: SingleChoiceElement[];
  no_elements_text: string | null;
  frozen: boolean;
  label: string | null;
  input_hint: string | null;
};
export type CascadingSingleChoice = FormSpec & {
  type: "cascading_single_choice";
  elements: CascadingSingleChoiceElement[];
  label: string | null;
  input_hint: unknown;
  layout: CascadingSingleChoiceLayout;
};
export type CascadingSingleChoiceLayout = "vertical" | "horizontal" | "button_group";
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
};
export type DataSize = FormSpec & {
  type: "data_size";
  label: string | null;
  displayed_magnitudes: string[];
  input_hint: string | null;
};
export type Catalog = FormSpec & {
  type: "catalog";
  topics: Topic[];
};
export type DualListChoice = (FormSpec & {
  elements: MultipleChoiceElement[];
  show_toggle_all: boolean;
  i18n: DualListChoiceI18N;
}) & {
  type: "dual_list_choice";
};
export type CheckboxListChoice = FormSpec & {
  type: "checkbox_list_choice";
  elements: MultipleChoiceElement[];
};
export type TimeSpan = FormSpec & {
  type: "time_span";
  label: string | null;
  i18n: TimeSpanI18N;
  displayed_magnitudes: TimeSpanTimeMagnitude[];
  input_hint: number | null;
};
export type TimeSpanTimeMagnitude = "millisecond" | "second" | "minute" | "hour" | "day";
export type SingleChoiceEditable = FormSpec & {
  type: "single_choice_editable";
  config_entity_type: string;
  config_entity_type_specifier: string;
  elements: SingleChoiceElement[];
  i18n: SingleChoiceEditableI18N;
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
export type Labels = FormSpec & {
  type: "labels";
  i18n: LabelsI18N;
  autocompleter?: Autocompleter;
  max_labels: number;
};

export interface VueFormspecComponents {
  components?: Components;
  validation_message?: ValidationMessage;
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
export interface Autocompleter {
  fetch_method: "ajax_vs_autocomplete";
  data: {};
}
export interface DictionaryElement {
  ident: string;
  required: boolean;
  group: DictionaryGroup | null;
  default_value: unknown;
  parameter_form: FormSpec;
}
export interface DictionaryGroup {
  key: string | null;
  title: string | null;
  help: string | null;
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
}
export interface Topic {
  ident: string;
  dictionary: Dictionary;
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
}
export interface TimeSpanI18N {
  millisecond: string;
  second: string;
  minute: string;
  hour: string;
  day: string;
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
export interface LabelsI18N {
  add_some_labels: string;
  key_value_format_error: string;
  uniqueness_error: string;
  max_labels_reached: string;
}
export interface ValidationMessage {
  location: string[];
  message: string;
  invalid_value: unknown;
}
