<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref, computed } from 'vue'
import type {
  Dictionary,
  String,
  TwoColumnDictionary
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'
import CmkDropdown from '../CmkDropdown.vue'
import CmkLabel from '../CmkLabel.vue'

defineProps<{ screenshotMode: boolean }>()

const GROUPS = {
  none: null,
  horizontal: {
    help: '',
    key: 'nullnull',
    layout: 'horizontal',
    title: 'Horizontal group'
  },
  vertical: {
    help: '',
    key: 'nullnull',
    layout: 'vertical',
    title: 'Vertical group'
  }
}

const topLevelGroup = ref<keyof typeof GROUPS>('none')
const childGroup = ref<keyof typeof GROUPS>('none')

const GROUP_OPTIONS: { name: keyof typeof GROUPS; title: string }[] = [
  { name: 'none', title: 'No group' },
  { name: 'vertical', title: 'Vertical group' },
  { name: 'horizontal', title: 'Horizontal group' }
]

const DICT_TYPES = [
  { name: 'dictionary', title: 'One column' },
  { name: 'two_column_dictionary', title: 'Two columns' }
]

const dictType = ref<'dictionary' | 'two_column_dictionary'>('dictionary')

const dictionarySpec = computed(
  () =>
    ({
      additional_static_elements: {},
      elements: [
        {
          default_value: {
            name: '',
            prefix: 'ba3c74458aae9d95a43c9a7b27b58af93700e2e7bf850f82b493e3e742e77666'
          },
          group: GROUPS[topLevelGroup.value],
          name: 'service_name',
          parameter_form: {
            additional_static_elements: {},
            elements: [
              {
                default_value: 'ba3c74458aae9d95a43c9a7b27b58af93700e2e7bf850f82b493e3e742e77666',
                group: GROUPS[childGroup.value],
                name: 'prefix',
                parameter_form: {
                  elements: [
                    {
                      name: 'ba3c74458aae9d95a43c9a7b27b58af93700e2e7bf850f82b493e3e742e77666',
                      title: 'Use "HTTP(S)" as service name prefix'
                    },
                    {
                      name: '5dc808cc885eaa96b1822f3f61ed3c4205bc29915cb99ddb1896aa6bed29f414',
                      title: 'Do not use a prefix'
                    }
                  ],
                  frozen: false,
                  help: 'The prefix is automatically added to each service to be able to organize it. The prefix is static and will be HTTP for unencrypted endpoints and HTTPS if TLS encryption is used. Alternatively, you may choose not to use the prefix option.',
                  i18n_base: {
                    required: 'required'
                  },
                  input_hint: 'Please choose',
                  label: '',
                  no_elements_text: '',
                  title: 'Prefix',
                  type: 'single_choice',
                  validators: []
                },
                render_only: false,
                required: true
              },
              {
                default_value: '',
                group: GROUPS[childGroup.value],
                name: 'name',
                parameter_form: {
                  autocompleter: null,
                  field_size: 'MEDIUM',
                  help: 'The name is the individual part of the used service name. Choose a human readable and unique title to be able to find your service later in Checkmk.',
                  i18n_base: {
                    required: 'required'
                  },
                  input_hint: 'My service name',
                  label: null,
                  title: 'Name',
                  type: 'string',
                  validators: [
                    {
                      error_message: 'The minimum allowed length is 1.',
                      max_value: null,
                      min_value: 1,
                      type: 'length_in_range'
                    }
                  ]
                } as String,
                render_only: false,
                required: true
              }
            ],
            groups: [],
            help: '',
            i18n_base: {
              required: 'required'
            },
            layout: 'one_column',
            no_elements_text: '(no parameters)',
            title: 'Service name',
            type: 'dictionary',
            validators: []
          } as Dictionary,
          render_only: false,
          required: false
        },
        {
          default_value: '',
          group: GROUPS[topLevelGroup.value],
          name: 'some_string',
          parameter_form: {
            autocompleter: null,
            field_size: 'MEDIUM',
            help: 'A second string to showcase root level groups.',
            i18n_base: {
              required: 'required'
            },
            input_hint: null,
            label: null,
            title: 'Some string',
            type: 'string',
            validators: []
          } as String,
          render_only: false,
          required: false
        }
      ],
      groups: [],
      help: '',
      i18n_base: {
        required: 'required'
      },
      no_elements_text: '(no parameters)',
      title: '',
      type: dictType.value,
      validators: []
    }) as Dictionary | TwoColumnDictionary
)

const requiredDictionarySpec = computed(() => {
  const clone = structuredClone(dictionarySpec.value)
  clone.elements[0]!.required = true
  return clone
})

const data = ref<Record<string, string>>({})
const dataRequired = ref<Record<string, unknown>>({})
</script>

<template>
  <p>
    <CmkLabel>Dictionary type:</CmkLabel>
    <CmkDropdown
      v-model:selected-option="dictType"
      :options="{ type: 'fixed', suggestions: DICT_TYPES }"
      label="Group"
    />
  </p>
  <p>
    <CmkLabel>Dictionary top level group:</CmkLabel>
    <CmkDropdown
      v-model:selected-option="topLevelGroup"
      :options="{ type: 'fixed', suggestions: GROUP_OPTIONS }"
      label="Group"
    />
  </p>
  <p>
    <CmkLabel>Dictionary element group:</CmkLabel>
    <CmkDropdown
      v-model:selected-option="childGroup"
      :options="{ type: 'fixed', suggestions: GROUP_OPTIONS }"
      label="Group"
    />
  </p>
  <h2>optional key:</h2>
  <FormEdit v-model:data="data" :spec="dictionarySpec" :backend-validation="[]" />
  <pre>{{ JSON.stringify(data) }}</pre>
  <h2>required key:</h2>
  <FormEdit v-model:data="dataRequired" :spec="requiredDictionarySpec" :backend-validation="[]" />
  <pre>{{ JSON.stringify(dataRequired) }}</pre>
</template>
