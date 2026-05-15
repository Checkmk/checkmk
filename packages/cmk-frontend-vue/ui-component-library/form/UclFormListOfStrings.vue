<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useMswWorker } from '@ucl/_ucl/composables/useMswWorker'
import type { ListOfStrings, String } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { HttpResponse, http } from 'msw'
import { ref } from 'vue'

import FormEdit from '@/form/FormEdit.vue'

async function interceptor({ request }: { request: Request }) {
  const jsonData = (await request.formData()).get('request')
  const query = JSON.parse(jsonData as string).value
  return HttpResponse.json({
    result: {
      choices: [
        [query, query],
        ['three', 'three'],
        ['two', 'two'],
        ['one', 'one']
      ]
    },
    result_code: 0,
    severity: 'success'
  })
}

const { mockLoaded } = useMswWorker([
  http.post(
    new RegExp(`${location.protocol}//${location.host}/ajax_vs_autocomplete.py`),
    interceptor
  )
])

defineProps<{ screenshotMode: boolean }>()

const autocompleterStringSpec: String = {
  type: 'string',
  title: '',
  help: '',
  validators: [],
  label: null,
  input_hint: '',
  field_size: 'MEDIUM',
  autocompleter: {
    data: {
      ident: 'config_hostname',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: true,
        world: 'world',
        context: {}
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  }
}

const autocompleterStringSpecWithHint: String = {
  ...autocompleterStringSpec,
  input_hint: '(Select hostname)'
}

const simpleStringSpec: String = {
  type: 'string',
  title: '',
  help: '',
  validators: [],
  label: null,
  input_hint: '',
  field_size: 'MEDIUM',
  autocompleter: null
}

function getSpec(additionalParams: Partial<ListOfStrings>): ListOfStrings {
  const spec: ListOfStrings = {
    type: 'list_of_strings',
    title: 'Hosts',
    help: '',
    validators: [],
    string_spec: simpleStringSpec,
    string_default_value: '',
    layout: 'vertical',
    ...additionalParams
  }
  return spec
}

const data = ref<Array<string>>(['some', 'value'])
const autocompleterEmptyData = ref<Array<string>>([])
const oneElementData1 = ref<Array<string>>([])
const manyElementsData1 = ref<Array<string>>(['1', '2', '3', '4', '5', '6'])
const oneElementData2 = ref<Array<string>>([])
const manyElementsData2 = ref<Array<string>>(['1', '2', '3', '4', '5', '6'])
</script>

<template>
  <span v-if="mockLoaded">
    <h2>With autocompleter</h2>
    <pre>{{ JSON.stringify(data) }}</pre>
    <FormEdit
      v-model:data="data"
      :spec="getSpec({ string_spec: autocompleterStringSpec })"
      :backend-validation="[]"
    />
    <h2>With autocompleter and input hint to show placeholder rendering</h2>
    <pre>{{ JSON.stringify(autocompleterEmptyData) }}</pre>
    <FormEdit
      v-model:data="autocompleterEmptyData"
      :spec="getSpec({ string_spec: autocompleterStringSpecWithHint })"
      :backend-validation="[]"
    />
  </span>
  <h2>Horizontal</h2>
  <h3>One element</h3>
  <FormEdit
    v-model:data="oneElementData1"
    :spec="getSpec({ layout: 'horizontal' })"
    :backend-validation="[]"
  />
  <h3>Many elements</h3>
  <FormEdit
    v-model:data="manyElementsData1"
    :spec="getSpec({ layout: 'horizontal' })"
    :backend-validation="[]"
  />
  <h2>Vertical</h2>
  <h3>One element</h3>
  <FormEdit
    v-model:data="oneElementData2"
    :spec="getSpec({ layout: 'vertical' })"
    :backend-validation="[]"
  />
  <h3>Many elements</h3>
  <FormEdit
    v-model:data="manyElementsData2"
    :spec="getSpec({ layout: 'vertical' })"
    :backend-validation="[]"
  />
</template>
