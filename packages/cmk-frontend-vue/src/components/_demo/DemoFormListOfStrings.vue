<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { onBeforeMount, onBeforeUnmount, ref } from 'vue'
import type { ListOfStrings, String } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'

import { http, HttpResponse } from 'msw'
import { setupWorker } from 'msw/browser'

async function interceptor() {
  return HttpResponse.json({
    result: {
      choices: [
        ['two', 'two'],
        ['one', 'one']
      ]
    },
    result_code: 0,
    severity: 'success'
  })
}
const worker = setupWorker(
  ...[
    http.post(
      new RegExp(`${location.protocol}//${location.host}/ajax_vs_autocomplete.py`),
      interceptor
    )
  ]
)

onBeforeMount(async () => {
  await worker.start()
  mockLoaded.value = true
})

onBeforeUnmount(() => {
  worker.stop()
})

const mockLoaded = ref<boolean>(false)

defineProps<{ screenshotMode: boolean }>()
const stringSpec: String = {
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
  },
  i18n_base: {
    required: 'required'
  }
}

const spec: ListOfStrings = {
  type: 'list_of_strings',
  title: 'Hosts',
  help: '',
  validators: [],
  string_spec: stringSpec,
  string_default_value: '',
  layout: 'horizontal'
}

const data = ref<Array<string>>(['some', 'value'])
</script>

<template>
  <h2>With autocompleter</h2>
  <pre>{{ JSON.stringify(data) }}</pre>
  <span v-if="mockLoaded">
    <FormEdit v-model:data="data" :spec="spec" :backend-validation="[]" />
  </span>
</template>
