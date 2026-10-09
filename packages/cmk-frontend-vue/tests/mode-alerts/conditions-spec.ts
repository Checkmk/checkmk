/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  BinaryConditionChoices,
  BooleanChoice,
  Dictionary,
  ListOfStrings,
  SingleChoice,
  String as StringSpec
} from 'cmk-shared-typing/typescript/vue_formspec_components'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

// Like the Setup page, the folder choice offers option ids instead of paths.
export const MAIN_FOLDER = 'option-main'
const LINUX_FOLDER = 'option-linux'
export const FOLDER_PATHS = { [MAIN_FOLDER]: '', [LINUX_FOLDER]: 'linux' }

// The Setup page registers the form components on start, a test has to do it itself.
initializeComponentRegistry()

const folderChoice: SingleChoice = {
  type: 'single_choice',
  title: 'Folder',
  help: 'Rule only applies to hosts directly in or below this folder.',
  validators: [],
  elements: [
    { name: MAIN_FOLDER, title: 'Main' },
    { name: LINUX_FOLDER, title: 'Main/Linux' }
  ],
  no_elements_text: null,
  frozen: false,
  label: null,
  input_hint: null
}

const hostName: StringSpec = {
  type: 'string',
  title: '',
  help: '',
  validators: [],
  label: null,
  input_hint: null,
  field_size: 'medium',
  autocompleter: null
}

const hostNames: ListOfStrings = {
  type: 'list_of_strings',
  title: '',
  help: '',
  validators: [
    {
      type: 'length_in_range',
      min_value: 1,
      max_value: null,
      error_message: 'Please add at least one host.'
    }
  ],
  string_spec: hostName,
  string_default_value: '',
  layout: 'horizontal'
}

const negate: BooleanChoice = {
  type: 'boolean_choice',
  title: '',
  help: '',
  validators: [],
  label: 'Negate: apply to all except listed hosts above',
  text_on: 'on',
  text_off: 'off'
}

const explicitHosts: Dictionary = {
  type: 'dictionary',
  title: 'Explicit hosts',
  help: '',
  validators: [],
  groups: [],
  no_elements_text: '',
  additional_static_elements: null,
  elements: [
    {
      name: 'value',
      required: true,
      group: null,
      default_value: [],
      render_only: false,
      parameter_form: hostNames
    },
    {
      name: 'negate',
      required: true,
      group: null,
      default_value: false,
      render_only: false,
      parameter_form: negate
    }
  ]
}

const hostLabelGroups: BinaryConditionChoices = {
  type: 'binary_condition_choices',
  title: 'Host labels',
  help: 'Rule only applies to hosts matching the label conditions.',
  validators: [
    {
      type: 'length_in_range',
      min_value: 1,
      max_value: null,
      error_message: 'Please add at least one host label.'
    }
  ],
  label: 'Label',
  autocompleter: {
    fetch_method: 'rest_autocomplete',
    data: { ident: 'label', params: { world: 'core', object_type: 'host' } }
  }
}

// Part of the rule editor's explicit conditions, as the Setup page serializes it.
export const CONDITIONS_SPEC: Dictionary = {
  type: 'dictionary',
  title: '',
  help: '',
  validators: [],
  groups: [],
  no_elements_text: '',
  additional_static_elements: null,
  elements: [
    {
      name: 'folder_path',
      required: true,
      group: null,
      default_value: '',
      render_only: false,
      parameter_form: folderChoice
    },
    {
      name: 'host_label_groups',
      required: false,
      group: null,
      default_value: [],
      render_only: false,
      parameter_form: hostLabelGroups
    },
    {
      name: 'explicit_hosts',
      required: false,
      group: null,
      default_value: { value: [], negate: false },
      render_only: false,
      parameter_form: explicitHosts
    }
  ]
}
