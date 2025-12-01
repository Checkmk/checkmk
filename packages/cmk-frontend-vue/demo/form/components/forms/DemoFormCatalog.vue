<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  Catalog,
  String as FormString,
  Integer,
  SimplePassword
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
      name: 'ungrouped_basic_inputs',
      title: 'Basic Inputs (Ungrouped)',
      elements: [
        {
          type: 'topic_element',
          name: 'simple_text',
          required: true,
          parameter_form: {
            type: 'string',
            title: 'Required Text Field',
            help: 'This is an ungrouped text input field for basic testing - it is required',
            label: 'Enter your name',
            input_hint: 'John Doe',
            field_size: 'MEDIUM',
            autocompleter: null,
            validators: [
              {
                type: 'length_in_range',
                min_value: 3,
                max_value: 50,
                error_message: 'Name must be between 3 and 50 characters'
              }
            ]
          } as FormString,
          default_value: ''
        },
        {
          type: 'topic_element',
          name: 'integer_field',
          required: true,
          parameter_form: {
            type: 'integer',
            title: 'Required Integer Field',
            help: 'A required integer field for testing validation on ungrouped numeric inputs',
            label: 'Port Number',
            unit: null,
            input_hint: '8080',
            validators: [
              {
                type: 'number_in_range',
                min_value: 1,
                max_value: 65535,
                error_message: 'Port must be between 1 and 65535'
              }
            ]
          } as Integer,
          default_value: 0
        }
      ],
      locked: null
    },
    {
      name: 'user_authentication',
      title: 'User Authentication (Grouped)',
      elements: [
        {
          type: 'topic_group',
          title: 'Basic Credentials',
          elements: [
            {
              type: 'topic_element',
              name: 'username',
              required: true,
              parameter_form: {
                type: 'string',
                title: 'Username',
                help: 'Enter the username for authentication',
                label: 'Username',
                input_hint: 'admin',
                field_size: 'MEDIUM',
                autocompleter: null,
                validators: []
              } as FormString,
              default_value: ''
            },
            {
              type: 'topic_element',
              name: 'simple_password',
              required: true,
              parameter_form: {
                type: 'simple_password',
                title: 'Password',
                help: 'Enter your password',
                label: 'Password',
                input_hint: 'Enter password...',
                validators: [
                  {
                    type: 'length_in_range',
                    min_value: 8,
                    max_value: 128,
                    error_message: 'Password must be between 8 and 128 characters'
                  }
                ]
              } as SimplePassword,
              default_value: ''
            }
          ]
        },
        {
          type: 'topic_group',
          title: 'Advanced Settings',
          elements: [
            {
              type: 'topic_element',
              name: 'session_timeout',
              required: false,
              parameter_form: {
                type: 'integer',
                title: 'Session Timeout',
                help: 'Session timeout in minutes',
                label: 'Timeout (minutes)',
                unit: 'min',
                input_hint: '30',
                validators: [
                  {
                    type: 'number_in_range',
                    min_value: 5,
                    max_value: 240,
                    error_message: 'Session timeout must be between 5 and 240 minutes'
                  }
                ]
              } as Integer,
              default_value: 30
            }
          ]
        }
      ],
      locked: null
    },
    {
      name: 'ungrouped_locked',
      title: 'Ungrouped (locked)',
      elements: [
        {
          type: 'topic_element',
          name: 'simple_text',
          required: true,
          parameter_form: {
            type: 'string',
            title: 'Required Text Field',
            help: 'This is an ungrouped text input field for basic testing - it is required',
            label: 'Enter your name',
            input_hint: 'John Doe',
            field_size: 'MEDIUM',
            autocompleter: null,
            validators: [
              {
                type: 'length_in_range',
                min_value: 3,
                max_value: 50,
                error_message: 'Name must be between 3 and 50 characters'
              }
            ]
          } as FormString,
          default_value: ''
        }
      ],
      locked: { message: 'This topic is locked' }
    },
    {
      name: 'grouped_locked',
      title: 'Grouped (locked)',
      elements: [
        {
          type: 'topic_group',
          title: 'Basic Credentials',
          elements: [
            {
              type: 'topic_element',
              name: 'simple_text',
              required: true,
              parameter_form: {
                type: 'string',
                title: 'Required Text Field',
                help: 'This is an ungrouped text input field for basic testing - it is required',
                label: 'Enter your name',
                input_hint: 'John Doe',
                field_size: 'MEDIUM',
                autocompleter: null,
                validators: [
                  {
                    type: 'length_in_range',
                    min_value: 3,
                    max_value: 50,
                    error_message: 'Name must be between 3 and 50 characters'
                  }
                ]
              } as FormString,
              default_value: ''
            }
          ]
        }
      ],
      locked: { message: 'This topic is locked' }
    }
  ]
})

const data = ref<Record<string, Record<string, unknown>>>({
  ungrouped_basic_inputs: {
    simple_text: 'Jo',
    integer_field: 99999
  },
  user_authentication: {
    username: 'admin user',
    simple_password: 'short',
    session_timeout: 300
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
      // UNGROUPED VALIDATIONS
      {
        location: ['ungrouped_basic_inputs', 'simple_text'],
        message: 'Name must be at least 3 characters long and cannot contain numbers',
        replacement_value: 'John Doe'
      },
      {
        location: ['ungrouped_basic_inputs', 'integer_field'],
        message: 'Port number must be between 1 and 65535',
        replacement_value: 8080
      },
      // GROUPED VALIDATIONS
      {
        location: ['user_authentication', 'username'],
        message: 'Username must not contain spaces or special characters',
        replacement_value: 'admin_user'
      },
      {
        location: ['user_authentication', 'simple_password'],
        message: 'Password must be at least 8 characters with numbers and letters',
        replacement_value: 'strongPassword123'
      },

      {
        location: ['user_authentication', 'session_timeout'],
        message: 'Session timeout must be between 5 and 240 minutes',
        replacement_value: 30
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
