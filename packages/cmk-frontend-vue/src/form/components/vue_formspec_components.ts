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
  | Tuple
  | OptionalChoice
  | SimplePassword
  | ListOfStrings
  | Folder;
export type Integer = FormSpec & {
  type: "integer";
  label?: string;
  unit?: string;
  input_hint?: string;
};
export type Validator = IsInteger | IsFloat | NumberInRange | LengthInRange | MatchRegex;
export type Float = FormSpec & {
  type: "float";
  label?: string;
  unit?: string;
  input_hint?: string;
};
export type String = FormSpec & {
  type: "string";
  placeholder?: string;
  input_hint?: string;
  field_size?: StringFieldSize;
  autocompleter?: Autocompleter;
};
export type StringFieldSize = "SMALL" | "MEDIUM" | "LARGE";
export type Dictionary = FormSpec & {
  type: "dictionary";
  elements: DictionaryElement[];
  groups: DictionaryGroup[];
  no_elements_text?: string;
  additional_static_elements?: {};
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
  input_html?: string;
  readonly_html?: string;
  varprefix: string;
};
export type SingleChoice = FormSpec & {
  type: "single_choice";
  elements: SingleChoiceElement[];
  no_elements_text?: string;
  frozen: boolean;
  label?: string;
  input_hint: string;
};
export type CascadingSingleChoice = FormSpec & {
  type: "cascading_single_choice";
  elements: CascadingSingleChoiceElement[];
  no_elements_text?: string;
  label?: string;
  input_hint: unknown;
  layout: CascadingChoiceLayout;
};
export type CascadingChoiceLayout = "vertical" | "horizontal";
export type FixedValue = FormSpec & {
  type: "fixed_value";
  label?: string;
  value: unknown;
};
export type BooleanChoice = FormSpec & {
  type: "boolean_choice";
  label?: string;
  text_on: string;
  text_off: string;
};
export type MultilineText = (FormSpec & {
  label?: string;
  macro_support?: boolean;
  monospaced?: boolean;
  input_hint?: string;
}) & {
  type: "multiline_text";
};
export type CommentTextArea = ((FormSpec & {
  label?: string;
  macro_support?: boolean;
  monospaced?: boolean;
  input_hint?: string;
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
  label?: string;
  displayed_magnitudes: string[];
  input_hint?: string;
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
  type?: "time_span";
  label?: string;
  i18n: TimeSpanI18N;
  displayed_magnitudes: TimeSpanTimeMagnitude[];
  input_hint?: number;
};
export type TimeSpanTimeMagnitude = "millisecond" | "second" | "minute" | "hour" | "day";
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
  layout?: ListOfStringsLayout;
};
export type ListOfStringsLayout = "horizontal" | "vertical";
export type Folder = FormSpec & {
  type: "folder";
  input_hint?: string;
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
  error_message?: string;
}
export interface IsFloat {
  type: "is_float";
  error_message?: string;
}
export interface NumberInRange {
  type: "number_in_range";
  min_value?: number;
  max_value?: number;
  error_message?: string;
}
export interface LengthInRange {
  type: "length_in_range";
  min_value?: number;
  max_value?: number;
  error_message?: string;
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
  group?: DictionaryGroup;
  default_value: unknown;
  parameter_form: FormSpec;
}
export interface DictionaryGroup {
  key: string;
  title: string;
  help?: string;
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
export interface I18NOptionalChoice {
  label?: string;
  none_label?: string;
}
export interface ValidationMessage {
  location: string[];
  message: string;
  invalid_value: unknown;
}
