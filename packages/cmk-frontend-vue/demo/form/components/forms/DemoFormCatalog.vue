<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  BooleanChoice,
  Catalog,
  String as FormString,
  Integer,
  MultilineText,
  SingleChoice
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormEdit from '@/form/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<Catalog>({
  type: 'catalog',
  title: 'Form Catalog Demo',
  help: 'This is a demo catalog containing multiple form elements organized in topics',
  validators: [],
  elements: [
    {
      name: 'basic_inputs',
      title: 'Basic Inputs',
      elements: [
        {
          type: 'topic_element',
          name: 'text_input',
          required: false,
          parameter_form: {
            type: 'string',
            title: 'Text Input',
            help: 'A simple text input field',
            label: 'Enter some text',
            input_hint: 'Type here...',
            field_size: 'MEDIUM',
            autocompleter: null,
            validators: []
          } as FormString,
          default_value: ''
        },
        {
          type: 'topic_element',
          name: 'number_input',
          required: true,
          parameter_form: {
            type: 'integer',
            title: 'Number Input',
            help: 'An integer input with validation',
            label: 'Enter a number',
            unit: null,
            input_hint: '42',
            validators: []
          } as Integer,
          default_value: 0
        }
      ]
    },
    {
      name: 'advanced_inputs',
      title: 'Advanced Inputs',
      elements: [
        {
          type: 'topic_element',
          name: 'choice_input',
          required: false,
          parameter_form: {
            type: 'single_choice',
            title: 'Single Choice',
            help: 'Choose one option from the list',
            label: 'Select an option',
            input_hint: null,
            frozen: false,
            no_elements_text: 'No options available',
            elements: [
              { name: 'option1', title: 'Option 1' },
              { name: 'option2', title: 'Option 2' },
              { name: 'option3', title: 'Option 3' }
            ],
            validators: []
          } as SingleChoice,
          default_value: 'option1'
        },
        {
          type: 'topic_element',
          name: 'boolean_input',
          required: false,
          parameter_form: {
            type: 'boolean_choice',
            title: 'Boolean Choice',
            help: 'A simple on/off toggle',
            label: 'Enable feature',
            text_on: 'Enabled',
            text_off: 'Disabled',
            validators: []
          } as BooleanChoice,
          default_value: false
        }
      ]
    },
    {
      name: 'text_areas',
      title: 'Text Areas',
      elements: [
        {
          type: 'topic_element',
          name: 'multiline_text',
          required: false,
          parameter_form: {
            type: 'multiline_text',
            title: 'Multiline Text',
            help: 'A larger text area for longer content',
            label: 'Description',
            input_hint: 'Enter detailed description...',
            macro_support: false,
            monospaced: false,
            validators: []
          } as MultilineText,
          default_value: ''
        }
      ]
    }
  ]
})

const data = ref<Record<string, Record<string, unknown>>>({
  basic_inputs: {
    text_input: 'Hello World',
    number_input: 42
  },
  advanced_inputs: {
    choice_input: 'option2',
    boolean_input: true
  },
  text_areas: {
    multiline_text: 'This is a sample multiline text\nwith multiple lines\nfor demonstration.'
  }
})

const validation = computed(() => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'General catalog validation: Please review all fields',
        replacement_value: null
      },
      {
        location: ['basic_inputs', 'text_input'],
        message: 'Text must be at least 5 characters long',
        replacement_value: 'Valid text input'
      },
      {
        location: ['basic_inputs', 'number_input'],
        message: 'Number must be between 1 and 100',
        replacement_value: 50
      },
      {
        location: ['advanced_inputs', 'choice_input'],
        message: 'Please select option1 or option3',
        replacement_value: 'option1'
      },
      {
        location: ['text_areas', 'multiline_text'],
        message: 'Description should include at least two sentences',
        replacement_value:
          'This is a proper description. It contains multiple sentences for better documentation.'
      }
    ]
  } else {
    return []
  }
})

const showValidation = ref<boolean>(false)
</script>

<template>
  <div>
    <CmkCheckbox v-model="showValidation" label="show validation" />
  </div>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
