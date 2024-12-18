<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
import type {
  Dictionary,
  FixedValue,
  String
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const embeddedSpec: String = {
  type: 'string',
  title: 'some string title',
  help: 'some string help',
  label: null,
  i18n_base: { required: 'required' },
  input_hint: 'some string input hint',
  field_size: 'SMALL',
  autocompleter: null,
  validators: []
}

const dictionarySpec: Dictionary = {
  type: 'dictionary',
  title: 'some title',
  help: 'some help',
  i18n_base: { required: 'required' },
  validators: [],
  no_elements_text: 'no elements text',
  additional_static_elements: null,
  layout: 'one_column',
  groups: [],
  elements: [
    {
      name: 'some_name',
      render_only: false,
      required: false,
      group: null,
      default_value: 'default_value',
      parameter_form: embeddedSpec
    },
    {
      name: 'unlabeled_fixed_value_null',
      render_only: false,
      required: false,
      group: null,
      default_value: null,
      parameter_form: {
        type: 'fixed_value',
        title: 'Unlabeled fixed value null',
        help: '',
        value: null,
        label: null,
        validators: []
      } as FixedValue
    },
    {
      name: 'unlabeled_fixed_value',
      render_only: false,
      required: false,
      group: null,
      default_value: null,
      parameter_form: {
        type: 'fixed_value',
        title: 'Unlabeled fixed value',
        help: '',
        value: 'fixed_value',
        label: null,
        validators: []
      } as FixedValue
    },
    {
      name: 'labeled_fixed_value',
      render_only: false,
      required: false,
      group: null,
      default_value: null,
      parameter_form: {
        type: 'fixed_value',
        title: 'Labeled fixed value',
        help: '',
        value: 'fixed_value',
        label: 'some label',
        validators: []
      } as FixedValue
    }
  ]
}

const spec = dictionarySpec
const specRequired = structuredClone(dictionarySpec)
specRequired.elements[0]!.required = true
const data = ref<Record<string, string>>({})

const dataRequired = ref<Record<string, unknown>>({
  some_name: 'some_value',
  labeled_fixed_value: 'fixed_value',
  unlabeled_fixed_value: 'fixed_value',
  unlabeled_fixed_value_null: null
})
</script>

<template>
  <h2>optional key:</h2>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="[]" />
  <h2>required key:</h2>
  <pre>{{ JSON.stringify(dataRequired) }}</pre>
  <FormEdit v-model:data="dataRequired" :spec="specRequired" :backend-validation="[]" />
</template>
