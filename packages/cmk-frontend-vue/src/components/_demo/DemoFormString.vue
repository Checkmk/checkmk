<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeMount, onBeforeUnmount, ref } from 'vue'
import type { String } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'
import CmkCheckbox from '@/components/CmkCheckbox.vue'

import { passthrough, http, HttpResponse } from 'msw'
import { setupWorker } from 'msw/browser'

const apiReturnsError = ref<boolean>(false)

const ALL: Array<string> = []
for (let i = 0; i < 200; i++) {
  ALL.push(window.crypto.randomUUID())
}

async function interceptor({ request }: { request: Request }) {
  if (apiReturnsError.value) {
    return HttpResponse.json({
      result:
        'some error very very very very very very very very very very very very very very very very very very very very very long message',
      result_code: 1,
      severity: 'error'
    })
  }

  const jsonData = (await request.formData()).get('request')
  if (jsonData === null) {
    throw new Error('could not find json data in form')
  }
  if (jsonData instanceof File) {
    throw new Error('got file, expected string')
  }
  const value = JSON.parse(jsonData).value

  const choices = ALL.filter((element: string) => element.includes(value)).map(
    (element: unknown) => [element, element]
  )
  return HttpResponse.json({
    result: {
      choices: choices
    },
    result_code: 0,
    severity: 'success'
  })
}
const worker = setupWorker(
  http.post(
    new RegExp(`${location.protocol}//${location.host}/ajax_vs_autocomplete.py`),
    interceptor
  ),
  http.get(/.+/, () => {
    return passthrough()
  })
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

const spec: String = {
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

const data = ref<string>('some thing')
</script>

<template>
  <input type="text" value="unrelated input field you can tab into" />
  <h2>With autocompleter</h2>
  <CmkCheckbox v-model="apiReturnsError" label="error in autocompleter" />
  <pre>{{ JSON.stringify(data) }}</pre>
  <span v-if="mockLoaded">
    <FormEdit v-model:data="data" :spec="spec" :backend-validation="[]" />
  </span>
  <br />
  <input type="text" value="unrelated input field you can tab into" />
  <br />
  <select>
    <option>asd</option>
    <option>bsd</option>
  </select>
  <br />
  <input type="text" value="unrelated input field you can tab into" />
  <br />
</template>
