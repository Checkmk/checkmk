<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
import type { Dictionary, String } from '@/form/components/vue_formspec_components'
import FormDictionary from '@/form/components/forms/FormDictionary.vue'

const embeddedSpec: String = {
  type: 'string',
  title: 'some string title',
  help: 'some string help',
  input_hint: 'some string input hint',
  field_size: 'SMALL',
  autocompleter: null,
  validators: []
}

const dictionarySpec: Dictionary = {
  type: 'dictionary',
  title: 'some title',
  help: 'some help',
  validators: [],
  no_elements_text: 'no elements text',
  additional_static_elements: null,
  layout: 'one_column',
  groups: [],
  elements: [
    {
      name: 'some_name',
      required: false,
      group: null,
      default_value: 'default_value',
      parameter_form: embeddedSpec
    }
  ]
}

const spec = dictionarySpec
const specRequired = structuredClone(dictionarySpec)
specRequired.elements[0]!.required = true
const data = ref<Record<string, string>>({})

const dataRequired = ref<Record<string, string>>({ some_name: 'some_value' })
</script>

<template>
  <h2>optional key:</h2>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormDictionary v-model:data="data" :spec="spec" :backend-validation="[]" />
  <h2>required key:</h2>
  <pre>{{ JSON.stringify(dataRequired) }}</pre>
  <FormDictionary v-model:data="dataRequired" :spec="specRequired" :backend-validation="[]" />
</template>
